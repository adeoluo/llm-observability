"""Searching and filtering spans across traces.

As trace volume grows, finding the relevant spans matters. :func:`search_spans` filters a
collection of traces by span name substring, status, a minimum duration, and attribute
matches, returning the spans that satisfy all supplied criteria. It is the query layer a
trace-storage backend would expose.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace


def search_spans(
    traces: Sequence[Trace],
    *,
    name_contains: str | None = None,
    status: SpanStatus | None = None,
    min_duration_ms: float | None = None,
    attributes: Mapping[str, Any] | None = None,
) -> list[Span]:
    """Return spans across ``traces`` matching all supplied filters.

    Args:
        traces: The traces to search.
        name_contains: Keep spans whose name contains this substring.
        status: Keep spans with this status.
        min_duration_ms: Keep spans at least this long.
        attributes: Keep spans whose attributes match all of these key/value pairs.
    """
    matches: list[Span] = []
    for trace in traces:
        for span in trace.spans:
            if name_contains is not None and name_contains not in span.name:
                continue
            if status is not None and span.status is not status:
                continue
            if min_duration_ms is not None and span.duration_ms < min_duration_ms:
                continue
            if attributes is not None and not _attributes_match(span, attributes):
                continue
            matches.append(span)
    return matches


def _attributes_match(span: Span, required: Mapping[str, Any]) -> bool:
    return all(span.attributes.get(key) == value for key, value in required.items())
