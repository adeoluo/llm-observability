"""Tests for auto-instrumentation, span events, and sampling."""

from __future__ import annotations

import itertools

import pytest

from llm_observability.core import Span, Tracer
from llm_observability.instrumentation import instrument
from llm_observability.sampling import AlwaysSampler, RatioSampler


# --------------------------------------------------------------------------- #
# Span events
# --------------------------------------------------------------------------- #
def test_span_add_event() -> None:
    span = Span(name="op", span_id="s1", trace_id="t1")
    span.add_event("cache_miss", timestamp=1.0, key="abc")
    assert len(span.events) == 1
    _when, name, attrs = span.events[0]
    assert name == "cache_miss"
    assert attrs["key"] == "abc"


def test_events_recorded_through_tracer() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("op") as span:
        span.add_event("started", timestamp=0.0)
        span.add_event("finished", timestamp=1.0)
    assert len(tracer.finished_spans[0].events) == 2


# --------------------------------------------------------------------------- #
# Instrumentation decorator
# --------------------------------------------------------------------------- #
def test_instrument_traces_function() -> None:
    tracer = Tracer(clock=itertools.count())

    @instrument(tracer, name="compute")
    def compute(x: int) -> int:
        return x * 2

    assert compute(21) == 42
    spans = tracer.finished_spans
    assert len(spans) == 1
    assert spans[0].name == "compute"


def test_instrument_nests() -> None:
    tracer = Tracer(clock=itertools.count())

    @instrument(tracer, name="inner")
    def inner() -> str:
        return "ok"

    @instrument(tracer, name="outer")
    def outer() -> str:
        return inner()

    outer()
    trace = tracer.traces()[0]
    assert len(trace) == 2
    root = trace.roots[0]
    assert root.span.name == "outer"
    assert root.children[0].span.name == "inner"


def test_instrument_records_error() -> None:
    tracer = Tracer(clock=itertools.count())

    @instrument(tracer, name="boom")
    def boom() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        boom()
    assert tracer.traces()[0].has_error


def test_instrument_preserves_metadata() -> None:
    tracer = Tracer(clock=itertools.count())

    @instrument(tracer)
    def documented() -> None:
        """A docstring."""

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "A docstring."


# --------------------------------------------------------------------------- #
# Sampling
# --------------------------------------------------------------------------- #
def test_always_sampler() -> None:
    sampler = AlwaysSampler()
    assert sampler.should_sample("anything")


def test_ratio_sampler_bounds() -> None:
    assert RatioSampler(1.0).should_sample("x")
    assert not RatioSampler(0.0).should_sample("x")


def test_ratio_sampler_deterministic() -> None:
    sampler = RatioSampler(0.5)
    assert sampler.should_sample("trace-abc") == sampler.should_sample("trace-abc")


def test_ratio_sampler_keeps_roughly_the_ratio() -> None:
    sampler = RatioSampler(0.3)
    kept = sum(1 for i in range(1000) if sampler.should_sample(f"trace-{i}"))
    # Hash-based sampling should land near 30% over many ids.
    assert 200 <= kept <= 400


def test_ratio_sampler_validates() -> None:
    with pytest.raises(ValueError, match="ratio"):
        RatioSampler(1.5)
