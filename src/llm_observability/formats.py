"""Additional export formats: Chrome trace, CSV, and span-flattening.

Beyond the tree view and JSON, these formats make traces consumable by standard tools and
spreadsheets:

- :func:`to_chrome_trace` - the Chrome Trace Event format, loadable directly in
  ``chrome://tracing`` or Perfetto for a visual flame chart.
- :func:`to_csv` - one row per span, for spreadsheets and ad-hoc analysis.

Both are pure functions over a :class:`~llm_observability.core.trace.Trace`.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from llm_observability.core.trace import Trace


def to_chrome_trace(trace: Trace) -> str:
    """Render a trace in the Chrome Trace Event format (JSON).

    Each span becomes a complete ("X") event with a start timestamp and duration in
    microseconds. Load the output in chrome://tracing or Perfetto.
    """
    events: list[dict[str, Any]] = []
    for span in trace.spans:
        events.append(
            {
                "name": span.name,
                "cat": "span",
                "ph": "X",
                "ts": span.start_time * 1_000_000,  # seconds -> microseconds
                "dur": span.duration_seconds * 1_000_000,
                "pid": 1,
                "tid": 1,
                "args": {"status": span.status.value, **span.attributes},
            }
        )
    return json.dumps({"traceEvents": events, "displayTimeUnit": "ms"}, indent=2)


def to_csv(trace: Trace) -> str:
    """Render a trace as CSV, one row per span."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["span_id", "parent_id", "name", "status", "duration_ms", "attributes"])
    for span in trace.spans:
        writer.writerow(
            [
                span.span_id,
                span.parent_id or "",
                span.name,
                span.status.value,
                f"{span.duration_ms:.3f}",
                json.dumps(span.attributes, sort_keys=True),
            ]
        )
    return buffer.getvalue()
