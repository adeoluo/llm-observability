"""Trace sampling.

In production, tracing every request is expensive. A sampler decides, per trace, whether
to keep it. Two strategies are provided:

- :class:`AlwaysSampler` - keep everything (the default, and what tests use).
- :class:`RatioSampler` - keep a fixed fraction deterministically, by hashing the trace id,
  so the decision is stable and reproducible for a given id and does not require shared
  state across processes.

A sampler is a simple predicate, so richer policies (keep all errors, rate-limit) compose
behind the same interface.
"""

from __future__ import annotations

import hashlib
from typing import Protocol, runtime_checkable


@runtime_checkable
class Sampler(Protocol):
    """Decides whether a trace should be kept."""

    def should_sample(self, trace_id: str) -> bool:
        """Return True to keep the trace identified by ``trace_id``."""
        ...


class AlwaysSampler:
    """Keeps every trace."""

    def should_sample(self, trace_id: str) -> bool:
        return True


class RatioSampler:
    """Keeps a fixed fraction of traces, decided deterministically by trace id."""

    def __init__(self, ratio: float) -> None:
        if not 0.0 <= ratio <= 1.0:
            raise ValueError("ratio must be in [0, 1]")
        self._ratio = ratio

    def should_sample(self, trace_id: str) -> bool:
        if self._ratio >= 1.0:
            return True
        if self._ratio <= 0.0:
            return False
        digest = hashlib.sha256(trace_id.encode("utf-8")).digest()
        # Map the first 8 bytes to a fraction in [0, 1) and compare to the ratio.
        bucket = int.from_bytes(digest[:8], "big") / float(1 << 64)
        return bucket < self._ratio
