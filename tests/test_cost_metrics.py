"""Tests for cost modeling and metric aggregation."""

from __future__ import annotations

import itertools

import pytest

from llm_observability.core import Tracer
from llm_observability.cost import DEFAULT_PRICES, ModelPrice, PriceList
from llm_observability.metrics import aggregate_metrics, record_llm_call


# --------------------------------------------------------------------------- #
# Cost
# --------------------------------------------------------------------------- #
def test_model_price_cost() -> None:
    price = ModelPrice(input_per_million=2.5, output_per_million=10.0)
    # 1M input + 1M output = 2.5 + 10 = 12.5
    assert price.cost(1_000_000, 1_000_000) == pytest.approx(12.5)


def test_model_price_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        ModelPrice(1.0, 1.0).cost(-1, 0)


def test_price_list_known_and_unknown() -> None:
    prices = PriceList()
    assert "gpt-4o" in prices
    assert prices.estimate_cost("gpt-4o", 1000, 1000) > 0.0
    assert prices.estimate_cost("unknown-model", 1000, 1000) == 0.0


def test_price_list_custom() -> None:
    prices = PriceList({"my-model": ModelPrice(1.0, 2.0)})
    assert prices.estimate_cost("my-model", 1_000_000, 0) == pytest.approx(1.0)


def test_default_prices_present() -> None:
    assert "claude-3-5-sonnet" in DEFAULT_PRICES


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def test_aggregate_metrics_sums_llm_calls() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("agent.run"):
        with tracer.span("llm.call") as s1:
            record_llm_call(s1, model="gpt-4o", input_tokens=1000, output_tokens=500)
        with tracer.span("llm.call") as s2:
            record_llm_call(s2, model="gpt-4o", input_tokens=2000, output_tokens=800)

    metrics = aggregate_metrics(tracer.traces()[0])
    assert metrics.llm_calls == 2
    assert metrics.input_tokens == 3000
    assert metrics.output_tokens == 1300
    assert metrics.total_tokens == 4300
    assert metrics.cost_usd > 0.0
    assert metrics.total_spans == 3


def test_aggregate_metrics_counts_errors() -> None:
    tracer = Tracer(clock=itertools.count())
    with pytest.raises(ValueError), tracer.span("root"):
        raise ValueError("boom")
    metrics = aggregate_metrics(tracer.traces()[0])
    assert metrics.errors == 1


def test_record_llm_call_rejects_negative_tokens() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("llm.call") as span, pytest.raises(ValueError, match="non-negative"):
        record_llm_call(span, model="gpt-4o", input_tokens=-1, output_tokens=0)


def test_metrics_format() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("llm.call") as span:
        record_llm_call(span, model="gpt-4o-mini", input_tokens=100, output_tokens=50)
    text = aggregate_metrics(tracer.traces()[0]).format()
    assert "1 calls" in text
    assert "150 tokens" in text


def test_non_llm_spans_not_counted_as_calls() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("agent.run"), tracer.span("tool.exec"):
        pass
    metrics = aggregate_metrics(tracer.traces()[0])
    assert metrics.llm_calls == 0
    assert metrics.total_spans == 2
