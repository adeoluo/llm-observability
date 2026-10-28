"""The :class:`Trace`: the tree of spans from one top-level operation.

A trace collects every span sharing a trace id and exposes the parent/child structure so
the run can be rendered, analyzed, and aggregated. The tree is reconstructed from each
span's ``parent_id``, so the trace does not need to be built in any particular order.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from llm_observability.core.span import Span, SpanStatus


@dataclass(frozen=True, slots=True)
class TraceNode:
    """A span together with its child nodes, forming the trace tree."""

    span: Span
    children: tuple[TraceNode, ...] = ()

    def walk(self) -> Iterator[Span]:
        """Yield this span and all descendants in depth-first order."""
        yield self.span
        for child in self.children:
            yield from child.walk()


class Trace:
    """All spans for a single trace id, with tree structure and aggregates."""

    def __init__(self, trace_id: str, spans: Sequence[Span]) -> None:
        if not spans:
            raise ValueError("a trace must contain at least one span")
        self._trace_id = trace_id
        self._spans = list(spans)
        self._roots = _build_forest(self._spans)

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    @property
    def roots(self) -> list[TraceNode]:
        """The top-level span nodes (those with no parent in this trace)."""
        return list(self._roots)

    def __len__(self) -> int:
        return len(self._spans)

    @property
    def total_duration_ms(self) -> float:
        """Wall-clock duration of the root spans."""
        return sum(node.span.duration_ms for node in self._roots)

    @property
    def has_error(self) -> bool:
        return any(span.status is SpanStatus.ERROR for span in self._spans)

    def spans_named(self, name: str) -> list[Span]:
        """Return all spans with the given name."""
        return [span for span in self._spans if span.name == name]


def _build_forest(spans: Sequence[Span]) -> list[TraceNode]:
    children_of: dict[str | None, list[Span]] = {}
    known_ids = {span.span_id for span in spans}
    for span in spans:
        parent = span.parent_id if span.parent_id in known_ids else None
        children_of.setdefault(parent, []).append(span)

    def build(span: Span) -> TraceNode:
        kids = children_of.get(span.span_id, [])
        kids.sort(key=lambda s: s.start_time)
        return TraceNode(span=span, children=tuple(build(child) for child in kids))

    roots = children_of.get(None, [])
    roots.sort(key=lambda s: s.start_time)
    return [build(root) for root in roots]
