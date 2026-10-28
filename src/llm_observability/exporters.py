"""Exporters: render and serialize traces.

Observability data is only useful if you can see it. This module renders a trace as an
indented tree (a waterfall-style view showing nesting, duration, and status) and
serializes a trace losslessly to and from JSON for storage and transport.
"""

from __future__ import annotations

import json
from typing import Any

from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace, TraceNode

_STATUS_MARK = {SpanStatus.OK: "ok", SpanStatus.ERROR: "ERR", SpanStatus.UNSET: "..."}


def render_tree(trace: Trace) -> str:
    """Render a trace as an indented tree with per-span duration and status."""
    lines: list[str] = [f"Trace {trace.trace_id} ({trace.total_duration_ms:.1f} ms)"]
    for root in trace.roots:
        _render_node(root, depth=0, lines=lines)
    return "\n".join(lines)


def _render_node(node: TraceNode, *, depth: int, lines: list[str]) -> None:
    indent = "  " * depth
    span = node.span
    mark = _STATUS_MARK[span.status]
    lines.append(f"{indent}- {span.name} [{mark}] {span.duration_ms:.1f} ms")
    for child in node.children:
        _render_node(child, depth=depth + 1, lines=lines)


def trace_to_dict(trace: Trace) -> dict[str, Any]:
    """Serialize a trace to a JSON-ready dictionary."""
    return {
        "trace_id": trace.trace_id,
        "spans": [
            {
                "name": span.name,
                "span_id": span.span_id,
                "trace_id": span.trace_id,
                "parent_id": span.parent_id,
                "start_time": span.start_time,
                "end_time": span.end_time,
                "status": span.status.value,
                "attributes": span.attributes,
            }
            for span in trace.spans
        ],
    }


def trace_to_json(trace: Trace, *, indent: int = 2) -> str:
    """Serialize a trace to a JSON string."""
    return json.dumps(trace_to_dict(trace), indent=indent)


def trace_from_dict(payload: dict[str, Any]) -> Trace:
    """Reconstruct a trace from :func:`trace_to_dict` output."""
    spans = [
        Span(
            name=item["name"],
            span_id=item["span_id"],
            trace_id=item["trace_id"],
            parent_id=item.get("parent_id"),
            start_time=item["start_time"],
            end_time=item.get("end_time"),
            status=SpanStatus(item.get("status", "unset")),
            attributes=dict(item.get("attributes", {})),
        )
        for item in payload["spans"]
    ]
    return Trace(payload["trace_id"], spans)


def trace_from_json(text: str) -> Trace:
    """Parse a trace from a JSON string."""
    return trace_from_dict(json.loads(text))
