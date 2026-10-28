"""Diffing two traces of the same operation.

When a change alters behavior, comparing a before-and-after trace pinpoints what moved.
:func:`diff_traces` aligns two traces by span name and reports which span names were added,
removed, or changed their total duration beyond a tolerance - the structural and
performance delta between two runs of the same workflow.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from llm_observability.core.trace import Trace


@dataclass(frozen=True, slots=True)
class DurationChange:
    """A span name whose aggregate duration changed between two traces."""

    name: str
    before_ms: float
    after_ms: float

    @property
    def delta_ms(self) -> float:
        return self.after_ms - self.before_ms

    @property
    def relative_change(self) -> float:
        if self.before_ms == 0.0:
            return 0.0
        return self.delta_ms / self.before_ms


@dataclass(frozen=True, slots=True)
class TraceDiff:
    """The structural and timing difference between two traces."""

    added: tuple[str, ...] = ()
    removed: tuple[str, ...] = ()
    changed: tuple[DurationChange, ...] = field(default_factory=tuple)

    @property
    def is_identical(self) -> bool:
        return not (self.added or self.removed or self.changed)


def _durations_by_name(trace: Trace) -> dict[str, float]:
    totals: dict[str, float] = {}
    for span in trace.spans:
        totals[span.name] = totals.get(span.name, 0.0) + span.duration_ms
    return totals


def diff_traces(before: Trace, after: Trace, *, tolerance: float = 0.10) -> TraceDiff:
    """Compare two traces by span name.

    Args:
        before: The baseline trace.
        after: The new trace.
        tolerance: Relative duration change below which a span is considered unchanged.
    """
    before_durations = _durations_by_name(before)
    after_durations = _durations_by_name(after)
    before_names = set(before_durations)
    after_names = set(after_durations)

    added = tuple(sorted(after_names - before_names))
    removed = tuple(sorted(before_names - after_names))

    changed: list[DurationChange] = []
    for name in sorted(before_names & after_names):
        change = DurationChange(name, before_durations[name], after_durations[name])
        if abs(change.relative_change) > tolerance:
            changed.append(change)

    return TraceDiff(added=added, removed=removed, changed=tuple(changed))
