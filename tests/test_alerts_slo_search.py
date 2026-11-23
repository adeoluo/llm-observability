"""Tests for alerting, SLO tracking, and span search."""

from __future__ import annotations

import itertools

import pytest

from llm_observability.alerts import (
    AlertEngine,
    Severity,
    max_cost,
    max_latency_ms,
    max_tokens,
    no_errors,
)
from llm_observability.core import Span, SpanStatus, Trace, Tracer
from llm_observability.metrics import record_llm_call
from llm_observability.search import search_spans
from llm_observability.slo import evaluate_slo


def _llm_trace(latency_ms: float, *, tokens: int = 1000, error: bool = False) -> Trace:
    span = Span(
        name="llm.call",
        span_id="s1",
        trace_id=f"t{latency_ms}",
        start_time=0.0,
        end_time=latency_ms / 1000.0,
        status=SpanStatus.ERROR if error else SpanStatus.OK,
    )
    record_llm_call(span, model="gpt-4o", input_tokens=tokens, output_tokens=tokens)
    return Trace(span.trace_id, [span])


# --------------------------------------------------------------------------- #
# Alerts
# --------------------------------------------------------------------------- #
def test_cost_rule_fires() -> None:
    engine = AlertEngine([max_cost(0.001)])
    alerts = engine.evaluate(_llm_trace(100, tokens=10000))
    assert any(a.rule_name == "max_cost" for a in alerts)


def test_latency_rule_fires() -> None:
    engine = AlertEngine([max_latency_ms(50)])
    assert engine.evaluate(_llm_trace(100))


def test_no_errors_rule_is_critical() -> None:
    engine = AlertEngine([no_errors()])
    alerts = engine.evaluate(_llm_trace(100, error=True))
    assert alerts[0].severity is Severity.CRITICAL


def test_rules_do_not_fire_when_within_limits() -> None:
    engine = AlertEngine([max_cost(1000.0), max_latency_ms(100000), max_tokens(10**9)])
    assert engine.evaluate(_llm_trace(10, tokens=1)) == []


def test_evaluate_batch() -> None:
    engine = AlertEngine([max_latency_ms(50)])
    alerts = engine.evaluate_batch([_llm_trace(100), _llm_trace(10)])
    assert len(alerts) == 1


# --------------------------------------------------------------------------- #
# SLO
# --------------------------------------------------------------------------- #
def test_slo_met() -> None:
    traces = [_llm_trace(100) for _ in range(9)] + [_llm_trace(500)]
    report = evaluate_slo(traces, threshold_ms=200, objective=0.9)
    assert report.compliance == 0.9
    assert report.met


def test_slo_breached() -> None:
    traces = [_llm_trace(500) for _ in range(5)] + [_llm_trace(100) for _ in range(5)]
    report = evaluate_slo(traces, threshold_ms=200, objective=0.95)
    assert not report.met
    assert report.error_budget_remaining < 0


def test_slo_format() -> None:
    report = evaluate_slo([_llm_trace(100)], threshold_ms=200)
    assert "SLO" in report.format()


def test_slo_validates() -> None:
    with pytest.raises(ValueError, match="empty batch"):
        evaluate_slo([], threshold_ms=100)
    with pytest.raises(ValueError, match="objective"):
        evaluate_slo([_llm_trace(100)], threshold_ms=100, objective=1.5)


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #
def _mixed_traces() -> list[Trace]:
    tracer = Tracer(clock=itertools.count(step=5))
    with tracer.span("agent.run"):
        with tracer.span("llm.call") as span:
            record_llm_call(span, model="gpt-4o", input_tokens=10, output_tokens=5)
        with tracer.span("tool.exec"):
            pass
    return tracer.traces()


def test_search_by_name() -> None:
    spans = search_spans(_mixed_traces(), name_contains="llm")
    assert all("llm" in s.name for s in spans)
    assert len(spans) == 1


def test_search_by_status() -> None:
    spans = search_spans(_mixed_traces(), status=SpanStatus.OK)
    assert len(spans) == 3


def test_search_by_attribute() -> None:
    spans = search_spans(_mixed_traces(), attributes={"llm.model": "gpt-4o"})
    assert len(spans) == 1


def test_search_by_min_duration() -> None:
    spans = search_spans(_mixed_traces(), min_duration_ms=1.0)
    assert all(s.duration_ms >= 1.0 for s in spans)


def test_search_combined_filters_no_match() -> None:
    spans = search_spans(_mixed_traces(), name_contains="llm", status=SpanStatus.ERROR)
    assert spans == []
