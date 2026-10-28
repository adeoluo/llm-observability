"""Analysis over many traces: summaries, percentiles, and regression detection.

A single trace tells you about one request; observability's value is in the aggregate.
This module summarizes a batch of traces (totals and latency percentiles) and detects
regressions between a baseline batch and a candidate batch - the loop a production system
runs to catch a deployment that made latency, cost, or error rate worse.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from llm_observability.core.trace import Trace
from llm_observability.metrics import aggregate_metrics


@dataclass(frozen=True, slots=True)
class BatchSummary:
    """Aggregated statistics over a batch of traces."""

    num_traces: int
    total_cost_usd: float
    total_tokens: int
    total_errors: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float

    @property
    def error_rate(self) -> float:
        return self.total_errors / self.num_traces if self.num_traces else 0.0

    def format(self) -> str:
        """Render a readable multi-line summary."""
        return (
            f"traces={self.num_traces}  cost=${self.total_cost_usd:.4f}  "
            f"tokens={self.total_tokens}  error_rate={self.error_rate:.1%}\n"
            f"latency p50={self.latency_p50_ms:.1f}ms  "
            f"p95={self.latency_p95_ms:.1f}ms  p99={self.latency_p99_ms:.1f}ms"
        )


def percentile(values: Sequence[float], q: float) -> float:
    """Return the ``q`` percentile (0-100) via linear interpolation."""
    if not values:
        return 0.0
    if not 0.0 <= q <= 100.0:
        raise ValueError("q must be in [0, 100]")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (q / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    fraction = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * fraction


def summarize_batch(traces: Sequence[Trace]) -> BatchSummary:
    """Summarize a batch of traces into totals and latency percentiles."""
    if not traces:
        raise ValueError("cannot summarize an empty batch")
    metrics = [aggregate_metrics(trace) for trace in traces]
    latencies = [m.latency_ms for m in metrics]
    return BatchSummary(
        num_traces=len(traces),
        total_cost_usd=sum(m.cost_usd for m in metrics),
        total_tokens=sum(m.total_tokens for m in metrics),
        total_errors=sum(1 for m in metrics if m.errors > 0),
        latency_p50_ms=percentile(latencies, 50),
        latency_p95_ms=percentile(latencies, 95),
        latency_p99_ms=percentile(latencies, 99),
    )


@dataclass(frozen=True, slots=True)
class RegressionAlert:
    """A detected regression on one metric between two batches."""

    metric: str
    baseline: float
    candidate: float
    relative_change: float


def detect_regressions(
    baseline: Sequence[Trace],
    candidate: Sequence[Trace],
    *,
    latency_tolerance: float = 0.20,
    cost_tolerance: float = 0.20,
    error_rate_tolerance: float = 0.05,
) -> list[RegressionAlert]:
    """Flag metrics that worsened from ``baseline`` to ``candidate``.

    Args:
        latency_tolerance: Allowed fractional increase in p95 latency.
        cost_tolerance: Allowed fractional increase in mean cost per trace.
        error_rate_tolerance: Allowed absolute increase in error rate.
    """
    base = summarize_batch(baseline)
    cand = summarize_batch(candidate)
    alerts: list[RegressionAlert] = []

    alerts.extend(
        _check_relative(
            "latency_p95_ms", base.latency_p95_ms, cand.latency_p95_ms, latency_tolerance
        )
    )
    base_cost = base.total_cost_usd / base.num_traces
    cand_cost = cand.total_cost_usd / cand.num_traces
    alerts.extend(_check_relative("cost_per_trace", base_cost, cand_cost, cost_tolerance))

    if cand.error_rate - base.error_rate > error_rate_tolerance:
        alerts.append(
            RegressionAlert(
                metric="error_rate",
                baseline=base.error_rate,
                candidate=cand.error_rate,
                relative_change=cand.error_rate - base.error_rate,
            )
        )
    return alerts


def _check_relative(
    metric: str, baseline: float, candidate: float, tolerance: float
) -> list[RegressionAlert]:
    if baseline <= 0.0:
        return []
    change = (candidate - baseline) / baseline
    if change > tolerance:
        return [RegressionAlert(metric, baseline, candidate, change)]
    return []
