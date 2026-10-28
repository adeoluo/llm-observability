"""Tests for additional export formats and trace diffing."""

from __future__ import annotations

import itertools
import json

from llm_observability.core import Span, SpanStatus, Trace, Tracer
from llm_observability.diff import diff_traces
from llm_observability.formats import to_chrome_trace, to_csv


def _trace() -> Trace:
    tracer = Tracer(clock=itertools.count(step=10))
    with tracer.span("agent.run"):
        with tracer.span("llm.call"):
            pass
        with tracer.span("tool.exec"):
            pass
    return tracer.traces()[0]


# --------------------------------------------------------------------------- #
# Chrome trace
# --------------------------------------------------------------------------- #
def test_chrome_trace_is_valid_json() -> None:
    payload = json.loads(to_chrome_trace(_trace()))
    assert "traceEvents" in payload
    assert len(payload["traceEvents"]) == 3
    assert all(event["ph"] == "X" for event in payload["traceEvents"])


def test_chrome_trace_has_durations_in_microseconds() -> None:
    payload = json.loads(to_chrome_trace(_trace()))
    # The root span spans 30 clock units (seconds) -> 30,000,000 microseconds.
    root = next(e for e in payload["traceEvents"] if e["name"] == "agent.run")
    assert root["dur"] > 0


# --------------------------------------------------------------------------- #
# CSV
# --------------------------------------------------------------------------- #
def test_csv_has_header_and_rows() -> None:
    csv_text = to_csv(_trace())
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("span_id,parent_id,name")
    assert len(lines) == 4  # header + 3 spans


def test_csv_includes_status() -> None:
    assert "ok" in to_csv(_trace())


# --------------------------------------------------------------------------- #
# Diffing
# --------------------------------------------------------------------------- #
def _trace_with(names_durations: list[tuple[str, float]]) -> Trace:
    spans = [
        Span(
            name=name,
            span_id=f"s{i}",
            trace_id="t1",
            start_time=0.0,
            end_time=duration / 1000.0,
            status=SpanStatus.OK,
        )
        for i, (name, duration) in enumerate(names_durations)
    ]
    return Trace("t1", spans)


def test_diff_identical() -> None:
    before = _trace_with([("a", 100.0), ("b", 200.0)])
    after = _trace_with([("a", 100.0), ("b", 200.0)])
    assert diff_traces(before, after).is_identical


def test_diff_detects_added_and_removed() -> None:
    before = _trace_with([("a", 100.0)])
    after = _trace_with([("b", 100.0)])
    diff = diff_traces(before, after)
    assert diff.added == ("b",)
    assert diff.removed == ("a",)


def test_diff_detects_duration_change() -> None:
    before = _trace_with([("a", 100.0)])
    after = _trace_with([("a", 300.0)])
    diff = diff_traces(before, after)
    assert len(diff.changed) == 1
    assert diff.changed[0].delta_ms == 200.0
    assert diff.changed[0].relative_change == 2.0


def test_diff_tolerance_suppresses_small_change() -> None:
    before = _trace_with([("a", 100.0)])
    after = _trace_with([("a", 105.0)])
    assert diff_traces(before, after, tolerance=0.1).is_identical
