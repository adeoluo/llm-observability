"""Service-level objective (SLO) tracking.

An SLO is a target such as "95% of requests complete under 2 seconds". :func:`evaluate_slo`
measures compliance over a batch of traces: the fraction meeting a latency threshold, and
whether that fraction meets the objective. This is the standard reliability metric that
turns raw latencies into a pass/fail health signal with an error budget.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from llm_observability.core.trace import Trace
from llm_observability.metrics import aggregate_metrics


@dataclass(frozen=True, slots=True)
class SloReport:
    """The outcome of evaluating a latency SLO."""

    threshold_ms: float
    objective: float
    compliance: float
    num_traces: int

    @property
    def met(self) -> bool:
        return self.compliance >= self.objective

    @property
    def error_budget_remaining(self) -> float:
        """Fraction of the allowed failures still unused (can be negative when breached)."""
        allowed_failure = 1.0 - self.objective
        actual_failure = 1.0 - self.compliance
        if allowed_failure == 0.0:
            return 1.0 if actual_failure == 0.0 else -1.0
        return (allowed_failure - actual_failure) / allowed_failure

    def format(self) -> str:
        status = "MET" if self.met else "BREACHED"
        return (
            f"SLO {status}: {self.compliance:.1%} of {self.num_traces} traces under "
            f"{self.threshold_ms:.0f} ms (objective {self.objective:.1%}, "
            f"budget {self.error_budget_remaining:+.1%})"
        )


def evaluate_slo(
    traces: Sequence[Trace],
    *,
    threshold_ms: float,
    objective: float = 0.95,
) -> SloReport:
    """Evaluate a latency SLO over a batch of traces.

    Args:
        traces: The traces to evaluate.
        threshold_ms: The per-trace latency threshold to meet.
        objective: The target compliance fraction (for example 0.95).
    """
    if not traces:
        raise ValueError("cannot evaluate an SLO over an empty batch")
    if not 0.0 < objective <= 1.0:
        raise ValueError("objective must be in (0, 1]")
    compliant = sum(1 for trace in traces if aggregate_metrics(trace).latency_ms <= threshold_ms)
    return SloReport(
        threshold_ms=threshold_ms,
        objective=objective,
        compliance=compliant / len(traces),
        num_traces=len(traces),
    )
