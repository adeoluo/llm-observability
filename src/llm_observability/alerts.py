"""An alerting rules engine over trace metrics.

Observability closes the loop by alerting when something is wrong. A :class:`Rule` is a
named predicate over a trace's aggregated :class:`~llm_observability.metrics.Metrics`, with
a severity; :class:`AlertEngine` evaluates a set of rules against a trace (or a batch) and
returns the firing alerts. Common rules (cost, latency, token, error ceilings) are
provided as constructors so a policy is a short, declarative list.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum

from llm_observability.core.trace import Trace
from llm_observability.metrics import Metrics, aggregate_metrics


class Severity(StrEnum):
    """How serious a fired alert is."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class Rule:
    """A named predicate over trace metrics with a severity."""

    name: str
    predicate: Callable[[Metrics], bool]
    severity: Severity = Severity.WARNING
    message: str = ""


@dataclass(frozen=True, slots=True)
class Alert:
    """A fired rule."""

    rule_name: str
    severity: Severity
    message: str


def max_cost(limit_usd: float, *, severity: Severity = Severity.WARNING) -> Rule:
    """A rule firing when a trace's cost exceeds ``limit_usd``."""
    return Rule(
        name="max_cost",
        predicate=lambda m: m.cost_usd > limit_usd,
        severity=severity,
        message=f"cost exceeded ${limit_usd:.4f}",
    )


def max_latency_ms(limit_ms: float, *, severity: Severity = Severity.WARNING) -> Rule:
    """A rule firing when a trace's latency exceeds ``limit_ms``."""
    return Rule(
        name="max_latency",
        predicate=lambda m: m.latency_ms > limit_ms,
        severity=severity,
        message=f"latency exceeded {limit_ms:.1f} ms",
    )


def max_tokens(limit: int, *, severity: Severity = Severity.WARNING) -> Rule:
    """A rule firing when a trace's total tokens exceed ``limit``."""
    return Rule(
        name="max_tokens",
        predicate=lambda m: m.total_tokens > limit,
        severity=severity,
        message=f"tokens exceeded {limit}",
    )


def no_errors(*, severity: Severity = Severity.CRITICAL) -> Rule:
    """A rule firing when a trace contains any error span."""
    return Rule(
        name="no_errors",
        predicate=lambda m: m.errors > 0,
        severity=severity,
        message="trace contains an error span",
    )


class AlertEngine:
    """Evaluates a set of rules against traces."""

    def __init__(self, rules: Sequence[Rule]) -> None:
        self._rules = tuple(rules)

    def evaluate(self, trace: Trace) -> list[Alert]:
        """Return the alerts firing for ``trace``."""
        metrics = aggregate_metrics(trace)
        return [
            Alert(rule.name, rule.severity, rule.message)
            for rule in self._rules
            if rule.predicate(metrics)
        ]

    def evaluate_batch(self, traces: Sequence[Trace]) -> list[Alert]:
        """Return all alerts firing across a batch of traces."""
        alerts: list[Alert] = []
        for trace in traces:
            alerts.extend(self.evaluate(trace))
        return alerts
