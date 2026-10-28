"""The :class:`Tracer`: creates spans and maintains the parent/child context.

The tracer is the instrumentation entry point. ``tracer.span("name")`` is a context
manager that opens a span, makes it the current parent for anything nested inside it, and
finishes it on exit - setting an ERROR status automatically if the block raises. This is
the ergonomic core that lets a whole agent run be traced with a few ``with`` blocks.

A context variable holds the current span, so nesting works correctly even across function
calls without threading a parent argument everywhere.
"""

from __future__ import annotations

import itertools
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace

_current_span: ContextVar[Span | None] = ContextVar("current_span", default=None)


class Tracer:
    """Creates spans, tracks nesting, and collects finished spans into traces."""

    def __init__(self, *, clock: itertools.count[int] | None = None) -> None:
        """Create a tracer.

        Args:
            clock: Optional deterministic counter used in place of the wall clock for
                span timing, so tests and demonstrations are reproducible.
        """
        self._spans: list[Span] = []
        self._clock = clock
        self._ids = itertools.count(1)

    def _now(self) -> float:
        if self._clock is not None:
            return float(next(self._clock))
        return time.perf_counter()

    def _new_id(self, prefix: str) -> str:
        if self._clock is not None:
            return f"{prefix}-{next(self._ids)}"
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    @contextmanager
    def span(self, name: str, **attributes: object) -> Iterator[Span]:
        """Open a span named ``name`` as a child of the current span.

        The span becomes the current parent for the duration of the block and is finished
        on exit, with an ERROR status if the block raises.
        """
        parent = _current_span.get()
        trace_id = parent.trace_id if parent is not None else self._new_id("trace")
        span = Span(
            name=name,
            span_id=self._new_id("span"),
            trace_id=trace_id,
            parent_id=parent.span_id if parent is not None else None,
            start_time=self._now(),
            attributes=dict(attributes),
        )
        token = _current_span.set(span)
        try:
            yield span
        except Exception:
            span.finish(status=SpanStatus.ERROR, end_time=self._now())
            self._spans.append(span)
            _current_span.reset(token)
            raise
        else:
            if not span.is_finished:
                span.finish(status=SpanStatus.OK, end_time=self._now())
            self._spans.append(span)
            _current_span.reset(token)

    @property
    def finished_spans(self) -> list[Span]:
        """All spans finished through this tracer, in completion order."""
        return list(self._spans)

    def traces(self) -> list[Trace]:
        """Group finished spans into traces by trace id."""
        by_trace: dict[str, list[Span]] = {}
        for span in self._spans:
            by_trace.setdefault(span.trace_id, []).append(span)
        return [Trace(trace_id, spans) for trace_id, spans in by_trace.items()]
