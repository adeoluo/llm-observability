"""Tests for spans, traces, and the tracer."""

from __future__ import annotations

import itertools

import pytest

from llm_observability.core import Span, SpanStatus, Tracer


# --------------------------------------------------------------------------- #
# Span
# --------------------------------------------------------------------------- #
def test_span_finish_sets_duration_and_status() -> None:
    span = Span(name="op", span_id="s1", trace_id="t1", start_time=0.0)
    span.finish(status=SpanStatus.OK, end_time=1.5)
    assert span.is_finished
    assert span.duration_seconds == 1.5
    assert span.duration_ms == 1500.0
    assert span.status is SpanStatus.OK


def test_span_double_finish_raises() -> None:
    span = Span(name="op", span_id="s1", trace_id="t1", start_time=0.0)
    span.finish(end_time=1.0)
    with pytest.raises(RuntimeError, match="already finished"):
        span.finish(end_time=2.0)


def test_span_attributes() -> None:
    span = Span(name="op", span_id="s1", trace_id="t1")
    span.set_attribute("model", "gpt-4o")
    assert span.attributes["model"] == "gpt-4o"


def test_unfinished_span_zero_duration() -> None:
    assert Span(name="op", span_id="s1", trace_id="t1").duration_seconds == 0.0


# --------------------------------------------------------------------------- #
# Tracer nesting
# --------------------------------------------------------------------------- #
def test_tracer_builds_nested_tree() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("agent.run"):
        with tracer.span("llm.call"):
            pass
        with tracer.span("tool.exec"):
            pass

    traces = tracer.traces()
    assert len(traces) == 1
    trace = traces[0]
    assert len(trace) == 3
    assert len(trace.roots) == 1
    root = trace.roots[0]
    assert root.span.name == "agent.run"
    assert [child.span.name for child in root.children] == ["llm.call", "tool.exec"]


def test_tracer_records_error_status() -> None:
    tracer = Tracer(clock=itertools.count())
    with pytest.raises(ValueError), tracer.span("failing"):
        raise ValueError("boom")
    span = tracer.finished_spans[0]
    assert span.status is SpanStatus.ERROR


def test_tracer_error_propagates_to_trace() -> None:
    tracer = Tracer(clock=itertools.count())
    with pytest.raises(RuntimeError), tracer.span("root"):
        raise RuntimeError("x")
    assert tracer.traces()[0].has_error


def test_sibling_spans_share_trace() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("root"):
        with tracer.span("a"):
            pass
        with tracer.span("b"):
            pass
    trace = tracer.traces()[0]
    assert len({s.trace_id for s in trace.spans}) == 1


def test_separate_roots_are_separate_traces() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("first"):
        pass
    with tracer.span("second"):
        pass
    assert len(tracer.traces()) == 2


def test_span_attributes_recorded_via_context() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("llm.call", model="gpt-4o") as span:
        span.set_attribute("tokens", 128)
    finished = tracer.finished_spans[0]
    assert finished.attributes["model"] == "gpt-4o"
    assert finished.attributes["tokens"] == 128


def test_trace_requires_spans() -> None:
    from llm_observability.core import Trace

    with pytest.raises(ValueError, match="at least one span"):
        Trace("t1", [])


def test_spans_named_lookup() -> None:
    tracer = Tracer(clock=itertools.count())
    with tracer.span("root"):
        with tracer.span("llm.call"):
            pass
        with tracer.span("llm.call"):
            pass
    assert len(tracer.traces()[0].spans_named("llm.call")) == 2
