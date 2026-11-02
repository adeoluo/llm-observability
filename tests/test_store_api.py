"""Tests for the trace store, the dashboard JSON API, static UI serving, and sample data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from llm_observability.cli import main
from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace
from llm_observability.demo import generate_sample_traces
from llm_observability.exporters import trace_to_dict
from llm_observability.metrics import record_llm_call
from llm_observability.service import (
    ObservabilityService,
    content_type_for,
    default_ui_dir,
    handle,
    resolve_ui_file,
)
from llm_observability.store import TraceFilter, TraceStore, list_traces, store_summary


def _trace(trace_id: str, *, model: str, latency_ms: float, error: bool, start: float) -> Trace:
    root = Span("agent.run", f"{trace_id}-root", trace_id, start_time=start)
    root.end_time = start + latency_ms / 1000.0
    root.status = SpanStatus.OK
    call = Span(
        "llm.call", f"{trace_id}-llm", trace_id, parent_id=root.span_id, start_time=start + 0.01
    )
    call.end_time = start + latency_ms / 2000.0
    call.status = SpanStatus.ERROR if error else SpanStatus.OK
    record_llm_call(call, model=model, input_tokens=100, output_tokens=40)
    return Trace(trace_id, [root, call])


def _service() -> ObservabilityService:
    service = ObservabilityService()
    service.store.extend(
        [
            _trace("t1", model="gpt-4o", latency_ms=300.0, error=False, start=100.0),
            _trace("t2", model="gpt-4o-mini", latency_ms=1200.0, error=True, start=200.0),
            _trace("t3", model="gpt-4o", latency_ms=800.0, error=False, start=300.0),
        ]
    )
    return service


def test_store_evicts_oldest_and_replaces() -> None:
    store = TraceStore(max_traces=2)
    store.add(_trace("a", model="gpt-4o", latency_ms=1, error=False, start=0))
    store.add(_trace("b", model="gpt-4o", latency_ms=1, error=False, start=1))
    store.add(_trace("a", model="gpt-4o", latency_ms=5, error=False, start=2))
    store.add(_trace("c", model="gpt-4o", latency_ms=1, error=False, start=3))
    assert len(store) == 2
    assert store.get("b") is None
    assert store.get("a") is not None
    with pytest.raises(ValueError):
        TraceStore(max_traces=0)


def test_list_traces_newest_first_with_summary_fields() -> None:
    status, payload = handle("GET", "/api/traces", {}, _service())
    assert status == 200
    assert payload["total"] == 3
    ids = [row["trace_id"] for row in payload["traces"]]
    assert ids == ["t3", "t2", "t1"]
    row = payload["traces"][1]
    assert row["status"] == "error"
    assert row["models"] == ["gpt-4o-mini"]
    assert row["name"] == "agent.run"
    assert row["duration_ms"] == pytest.approx(1200.0)
    assert row["total_tokens"] == 140
    assert row["span_count"] == 2
    assert row["cost_usd"] > 0


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("?status=error", ["t2"]),
        ("?status=ok", ["t3", "t1"]),
        ("?model=gpt-4o", ["t3", "t1"]),
        ("?min_latency_ms=500", ["t3", "t2"]),
        ("?status=ok&min_latency_ms=500&model=gpt-4o", ["t3"]),
        ("?limit=1", ["t3"]),
        ("?status=&model=", ["t3", "t2", "t1"]),
    ],
)
def test_list_traces_filters(query: str, expected: list[str]) -> None:
    status, payload = handle("GET", f"/api/traces{query}", {}, _service())
    assert status == 200
    assert [row["trace_id"] for row in payload["traces"]] == expected


@pytest.mark.parametrize(
    "query", ["?status=bogus", "?min_latency_ms=-1", "?min_latency_ms=abc", "?limit=0"]
)
def test_list_traces_rejects_bad_filters(query: str) -> None:
    status, payload = handle("GET", f"/api/traces{query}", {}, _service())
    assert status == 400
    assert "error" in payload


def test_get_trace_detail_and_missing() -> None:
    service = _service()
    status, payload = handle("GET", "/api/traces/t2", {}, service)
    assert status == 200
    assert payload["summary"]["trace_id"] == "t2"
    assert {span["name"] for span in payload["spans"]} == {"agent.run", "llm.call"}
    llm = next(span for span in payload["spans"] if span["name"] == "llm.call")
    assert llm["parent_id"] == "t2-root"
    assert llm["status"] == "error"
    assert llm["attributes"]["llm.model"] == "gpt-4o-mini"
    status, payload = handle("GET", "/api/traces/nope", {}, service)
    assert status == 404


def test_summary_endpoint() -> None:
    status, payload = handle("GET", "/api/summary", {}, _service())
    assert status == 200
    assert payload["traces"] == 3
    assert payload["total_tokens"] == 420
    assert payload["error_rate"] == pytest.approx(1 / 3, abs=1e-4)
    assert payload["latency_p50_ms"] == pytest.approx(800.0)
    assert payload["latency_p99_ms"] >= payload["latency_p95_ms"] >= payload["latency_p50_ms"]
    models = {entry["model"]: entry for entry in payload["by_model"]}
    assert models["gpt-4o"]["calls"] == 2
    assert models["gpt-4o-mini"]["output_tokens"] == 40


def test_summary_of_empty_store() -> None:
    payload = store_summary(TraceStore())
    assert payload["traces"] == 0
    assert payload["by_model"] == []


def test_ingest_traces_roundtrip() -> None:
    service = ObservabilityService()
    body = {"traces": [trace_to_dict(t) for t in generate_sample_traces(5)]}
    status, payload = handle("POST", "/api/traces", body, service)
    assert status == 201
    assert payload == {"ingested": 5, "stored": 5}
    assert list_traces(service.store, TraceFilter())["total"] == 5


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"traces": []},
        {"traces": ["x"]},
        {"traces": [{"trace_id": "a"}]},
        {"traces": [{"trace_id": "a", "spans": []}]},
        {"traces": [{"trace_id": "a", "spans": [{"name": "x"}]}]},
    ],
)
def test_ingest_rejects_invalid(body: dict[str, object]) -> None:
    status, payload = handle("POST", "/api/traces", body, ObservabilityService())
    assert status == 400
    assert "error" in payload


def test_trace_routes_share_one_metrics_label() -> None:
    service = _service()
    handle("GET", "/api/traces/t1", {}, service)
    handle("GET", "/api/traces/t2?x=1", {}, service)
    text = service.metrics.render_prometheus()
    assert 'route="GET /api/traces/{id}"' in text
    assert "t1" not in text


def test_resolve_ui_file(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html></html>")
    (tmp_path / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("x")
    assert resolve_ui_file(tmp_path, "/ui/") == (tmp_path / "index.html").resolve()
    assert resolve_ui_file(tmp_path, "/ui") == (tmp_path / "index.html").resolve()
    assert (
        resolve_ui_file(tmp_path, "/ui/assets/app.js?v=1")
        == (tmp_path / "assets" / "app.js").resolve()
    )
    assert resolve_ui_file(tmp_path, "/ui/../secret.txt") is None
    assert resolve_ui_file(tmp_path, "/ui/%2e%2e/secret.txt") is None
    assert resolve_ui_file(tmp_path, "/ui/missing.js") is None
    assert resolve_ui_file(tmp_path, "/uix/index.html") is None


def test_content_types_and_default_ui_dir() -> None:
    assert content_type_for(Path("a.js")).startswith("text/javascript")
    assert content_type_for(Path("index.HTML")).startswith("text/html")
    assert content_type_for(Path("blob.bin")) == "application/octet-stream"
    assert default_ui_dir().parts[-2:] == ("web", "dist")


def test_sample_traces_are_varied_and_reproducible() -> None:
    first = generate_sample_traces(120, seed=3)
    second = generate_sample_traces(120, seed=3)
    assert [trace_to_dict(t) for t in first] == [trace_to_dict(t) for t in second]
    roots = {trace.roots[0].span.name for trace in first}
    assert roots == {"chat.request", "rag.query", "agent.run"}
    assert any(trace.has_error for trace in first)
    assert not all(trace.has_error for trace in first)
    for trace in first:
        assert len(trace.roots) == 1
        root = trace.roots[0].span
        assert root.end_time is not None
        for span in trace.spans:
            assert span.end_time is not None
            assert root.start_time <= span.start_time <= span.end_time <= root.end_time
    assert generate_sample_traces(0) == []
    with pytest.raises(ValueError):
        generate_sample_traces(-1)


def test_cli_sample_traces(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "traces.json"
    assert main(["sample-traces", "--count", "4", "--output", str(target)]) == 0
    assert "wrote 4 traces" in capsys.readouterr().out
    payload = json.loads(target.read_text())
    assert len(payload["traces"]) == 4
    assert main(["sample-traces", "--count", "2"]) == 0
    assert len(json.loads(capsys.readouterr().out)["traces"]) == 2
