"""Tests for exporters and trace analysis."""

from __future__ import annotations

import itertools

import pytest

from llm_observability.analysis import (
    detect_regressions,
    percentile,
    summarize_batch,
)
from llm_observability.core import Span, SpanStatus, Trace, Tracer
from llm_observability.exporters import render_tree, trace_from_json, trace_to_json
from llm_observability.metrics import record_llm_call


def _llm_trace(latency: int, *, tokens: int = 1000, error: bool = False) -> Trace:
    """Build a one-span trace with controlled latency and token usage."""
    span = Span(
        name="llm.call",
        span_id="s1",
        trace_id=f"t{latency}",
        start_time=0.0,
        end_time=float(latency) / 1000.0,  # latency ms -> seconds
        status=SpanStatus.ERROR if error else SpanStatus.OK,
    )
    record_llm_call(span, model="gpt-4o", input_tokens=tokens, output_tokens=tokens)
    return Trace(span.trace_id, [span])


# --------------------------------------------------------------------------- #
# Exporters
# --------------------------------------------------------------------------- #
def test_render_tree_shows_nesting() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("agent.run"), tracer.span("llm.call"):
        pass
    tree = render_tree(tracer.traces()[0])
    assert "agent.run" in tree
    assert "  - llm.call" in tree


def test_trace_json_round_trip() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("agent.run"), tracer.span("llm.call") as span:
        record_llm_call(span, model="gpt-4o", input_tokens=10, output_tokens=5)
    original = tracer.traces()[0]
    restored = trace_from_json(trace_to_json(original))
    assert restored.trace_id == original.trace_id
    assert len(restored) == len(original)
    assert restored.spans_named("llm.call")[0].attributes["llm.model"] == "gpt-4o"


# --------------------------------------------------------------------------- #
# Percentiles
# --------------------------------------------------------------------------- #
def test_percentile_interpolates() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert percentile(values, 50) == 30.0
    assert percentile(values, 0) == 10.0
    assert percentile(values, 100) == 50.0


def test_percentile_single_value() -> None:
    assert percentile([42.0], 95) == 42.0


def test_percentile_validates_q() -> None:
    with pytest.raises(ValueError, match="q must"):
        percentile([1.0], 150)


# --------------------------------------------------------------------------- #
# Batch summary
# --------------------------------------------------------------------------- #
def test_summarize_batch() -> None:
    traces = [_llm_trace(100), _llm_trace(200), _llm_trace(300)]
    summary = summarize_batch(traces)
    assert summary.num_traces == 3
    assert summary.total_tokens == 6000
    assert summary.latency_p50_ms == 200.0
    assert summary.total_cost_usd > 0.0


def test_summarize_empty_raises() -> None:
    with pytest.raises(ValueError, match="empty batch"):
        summarize_batch([])


def test_error_rate() -> None:
    traces = [_llm_trace(100), _llm_trace(100, error=True)]
    assert summarize_batch(traces).error_rate == 0.5


# --------------------------------------------------------------------------- #
# Regression detection
# --------------------------------------------------------------------------- #
def test_detects_latency_regression() -> None:
    baseline = [_llm_trace(100) for _ in range(5)]
    candidate = [_llm_trace(300) for _ in range(5)]
    alerts = detect_regressions(baseline, candidate)
    metrics = {alert.metric for alert in alerts}
    assert "latency_p95_ms" in metrics


def test_no_regression_when_stable() -> None:
    baseline = [_llm_trace(100) for _ in range(5)]
    candidate = [_llm_trace(105) for _ in range(5)]
    assert detect_regressions(baseline, candidate) == []


def test_detects_error_rate_regression() -> None:
    baseline = [_llm_trace(100) for _ in range(10)]
    candidate = [_llm_trace(100, error=True) for _ in range(10)]
    alerts = detect_regressions(baseline, candidate)
    assert any(alert.metric == "error_rate" for alert in alerts)
