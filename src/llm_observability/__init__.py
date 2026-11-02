"""LLM Observability: tracing, metrics, a collector service, and a JSON API for a web dashboard.

Public API: the core tracing primitives. Metrics, cost, exporters, and analysis live in
their own modules.
"""

from __future__ import annotations

from llm_observability.core import Span, SpanStatus, Trace, TraceNode, Tracer

__version__ = "0.2.0"

__all__ = [
    "Span",
    "SpanStatus",
    "Trace",
    "TraceNode",
    "Tracer",
    "__version__",
]
