"""An in-memory trace store and the JSON views the dashboard reads.

The HTTP service keeps recently ingested traces in a bounded, thread-safe
:class:`TraceStore`. The helpers here turn stored traces into the JSON shapes served by the
read-only ``/api`` endpoints: a per-trace summary row for the list view, a full trace with
spans for the detail view, and a batch summary with a per-model breakdown for the overview.
"""

from __future__ import annotations

import threading
from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from llm_observability.analysis import summarize_batch
from llm_observability.core.trace import Trace
from llm_observability.exporters import trace_to_dict
from llm_observability.metrics import (
    ATTR_COST,
    ATTR_INPUT_TOKENS,
    ATTR_MODEL,
    ATTR_OUTPUT_TOKENS,
    aggregate_metrics,
)

JsonObject = dict[str, Any]


class TraceStore:
    """A bounded, thread-safe store of traces keyed by trace id (oldest evicted first)."""

    def __init__(self, max_traces: int = 10000) -> None:
        if max_traces <= 0:
            raise ValueError("max_traces must be positive")
        self._max_traces = max_traces
        self._traces: OrderedDict[str, Trace] = OrderedDict()
        self._lock = threading.Lock()

    def add(self, trace: Trace) -> None:
        """Insert or replace a trace, evicting the oldest when the store is full."""
        with self._lock:
            self._traces.pop(trace.trace_id, None)
            self._traces[trace.trace_id] = trace
            while len(self._traces) > self._max_traces:
                self._traces.popitem(last=False)

    def extend(self, traces: Iterable[Trace]) -> None:
        for trace in traces:
            self.add(trace)

    def get(self, trace_id: str) -> Trace | None:
        with self._lock:
            return self._traces.get(trace_id)

    def all(self) -> list[Trace]:
        with self._lock:
            return list(self._traces.values())

    def __len__(self) -> int:
        with self._lock:
            return len(self._traces)


def _trace_start(trace: Trace) -> float:
    return min(span.start_time for span in trace.spans)


def _trace_models(trace: Trace) -> list[str]:
    return sorted(
        {str(span.attributes[ATTR_MODEL]) for span in trace.spans if ATTR_MODEL in span.attributes}
    )


def trace_summary(trace: Trace) -> JsonObject:
    """Summarize one trace as a list-view row."""
    metrics = aggregate_metrics(trace)
    roots = trace.roots
    return {
        "trace_id": trace.trace_id,
        "name": roots[0].span.name if roots else "",
        "start_time": _trace_start(trace),
        "duration_ms": round(metrics.latency_ms, 3),
        "status": "error" if trace.has_error else "ok",
        "models": _trace_models(trace),
        "span_count": metrics.total_spans,
        "llm_calls": metrics.llm_calls,
        "input_tokens": metrics.input_tokens,
        "output_tokens": metrics.output_tokens,
        "total_tokens": metrics.total_tokens,
        "cost_usd": round(metrics.cost_usd, 6),
        "errors": metrics.errors,
    }


def trace_detail(trace: Trace) -> JsonObject:
    """Return a trace's summary together with all of its spans."""
    payload = trace_to_dict(trace)
    return {"summary": trace_summary(trace), "spans": payload["spans"]}


@dataclass(frozen=True, slots=True)
class TraceFilter:
    """Criteria for the trace list; ``None`` means no constraint."""

    status: str | None = None
    model: str | None = None
    min_latency_ms: float | None = None
    limit: int = 500

    def matches(self, row: JsonObject) -> bool:
        if self.status is not None and row["status"] != self.status:
            return False
        if self.model is not None and self.model not in row["models"]:
            return False
        return self.min_latency_ms is None or row["duration_ms"] >= self.min_latency_ms


def list_traces(store: TraceStore, criteria: TraceFilter) -> JsonObject:
    """Return matching trace rows, newest first, capped at ``criteria.limit``."""
    rows = [trace_summary(trace) for trace in store.all()]
    matching = [row for row in rows if criteria.matches(row)]
    matching.sort(key=lambda row: row["start_time"], reverse=True)
    return {"total": len(matching), "traces": matching[: criteria.limit]}


def store_summary(store: TraceStore) -> JsonObject:
    """Aggregate every stored trace: totals, latency percentiles, and a per-model breakdown."""
    traces = store.all()
    by_model: dict[str, JsonObject] = {}
    for trace in traces:
        for span in trace.spans:
            if ATTR_MODEL not in span.attributes:
                continue
            model = str(span.attributes[ATTR_MODEL])
            entry = by_model.setdefault(
                model,
                {
                    "model": model,
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                },
            )
            entry["calls"] += 1
            entry["input_tokens"] += int(span.attributes.get(ATTR_INPUT_TOKENS, 0))
            entry["output_tokens"] += int(span.attributes.get(ATTR_OUTPUT_TOKENS, 0))
            entry["cost_usd"] += float(span.attributes.get(ATTR_COST, 0.0))
    models = sorted(by_model.values(), key=lambda entry: str(entry["model"]))
    for entry in models:
        entry["cost_usd"] = round(entry["cost_usd"], 6)
    if not traces:
        return {
            "traces": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "error_rate": 0.0,
            "latency_p50_ms": 0.0,
            "latency_p95_ms": 0.0,
            "latency_p99_ms": 0.0,
            "by_model": [],
        }
    summary = summarize_batch(traces)
    return {
        "traces": summary.num_traces,
        "total_cost_usd": round(summary.total_cost_usd, 6),
        "total_tokens": summary.total_tokens,
        "error_rate": round(summary.error_rate, 4),
        "latency_p50_ms": round(summary.latency_p50_ms, 3),
        "latency_p95_ms": round(summary.latency_p95_ms, 3),
        "latency_p99_ms": round(summary.latency_p99_ms, 3),
        "by_model": models,
    }
