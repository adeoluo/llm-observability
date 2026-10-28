"""LLM Observability - a tracing and metrics platform built from scratch.

Public API: the core tracing primitives. Metrics, cost, exporters, and analysis live in
their own modules.
"""

from __future__ import annotations

from llm_observability.core import Span, SpanStatus, Trace, TraceNode, Tracer

__version__ = "0.1.0"

__all__ = [
    "Span",
    "SpanStatus",
    "Trace",
    "TraceNode",
    "Tracer",
    "__version__",
]
