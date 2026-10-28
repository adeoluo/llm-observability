"""Core span types for tracing.

A :class:`Span` is the unit of a trace: a named, timed operation with a parent, arbitrary
attributes, and an outcome. Spans form a tree (a child span's work happens inside its
parent's), which is exactly how an agent run or a retrieval pipeline decomposes - an
"agent.run" span containing "llm.call" and "tool.exec" spans.

Spans are mutable while open (duration and status are set on finish) and are identified by
stable ids so a trace can be serialized and reconstructed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SpanStatus(StrEnum):
    """The outcome of a span."""

    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass(slots=True)
class Span:
    """A single timed operation in a trace."""

    name: str
    span_id: str
    trace_id: str
    parent_id: str | None = None
    start_time: float = field(default_factory=time.perf_counter)
    end_time: float | None = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: dict[str, Any] = field(default_factory=dict)

    def set_attribute(self, key: str, value: Any) -> None:
        """Attach a key/value annotation to the span."""
        self.attributes[key] = value

    def finish(self, *, status: SpanStatus = SpanStatus.OK, end_time: float | None = None) -> None:
        """Mark the span complete, recording its end time and status."""
        if self.end_time is not None:
            raise RuntimeError(f"span {self.name!r} is already finished")
        self.end_time = end_time if end_time is not None else time.perf_counter()
        self.status = status

    @property
    def is_finished(self) -> bool:
        return self.end_time is not None

    @property
    def duration_seconds(self) -> float:
        """Elapsed time; 0.0 until the span is finished."""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time

    @property
    def duration_ms(self) -> float:
        return self.duration_seconds * 1000.0
