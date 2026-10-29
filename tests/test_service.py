"""Tests for the dependency-free HTTP observability service (pure handler layer)."""

from __future__ import annotations

from llm_observability.service import ObservabilityService, handle

_SERVICE = ObservabilityService()
_CALLS = [
    {"model": "gpt-4o", "input_tokens": 100, "output_tokens": 50, "latency_ms": 200.0},
    {
        "model": "gpt-4o",
        "input_tokens": 200,
        "output_tokens": 80,
        "latency_ms": 900.0,
        "error": True,
    },
    {"model": "gpt-4o-mini", "input_tokens": 50, "output_tokens": 20, "latency_ms": 120.0},
]


def test_health() -> None:
    status, payload = handle("GET", "/health", {}, _SERVICE)
    assert status == 200
    assert payload["status"] == "ok"
    assert "gpt-4o" in payload["models"]


def test_summarize_metrics() -> None:
    status, payload = handle("POST", "/summarize", {"calls": _CALLS}, _SERVICE)
    assert status == 200
    assert payload["traces"] == 3
    assert payload["total_tokens"] == 500
    assert payload["error_rate"] > 0
    assert payload["latency_p99_ms"] >= payload["latency_p50_ms"]
    assert "slo" not in payload


def test_summarize_with_slo() -> None:
    status, payload = handle(
        "POST", "/summarize", {"calls": _CALLS, "slo_threshold_ms": 500}, _SERVICE
    )
    assert status == 200
    assert "slo" in payload
    assert payload["slo"]["threshold_ms"] == 500.0
    assert 0.0 <= payload["slo"]["compliance"] <= 1.0


def test_summarize_rejects_empty_calls() -> None:
    status, payload = handle("POST", "/summarize", {"calls": []}, _SERVICE)
    assert status == 400
    assert "calls" in payload["error"]


def test_summarize_rejects_missing_fields() -> None:
    status, _ = handle("POST", "/summarize", {"calls": [{"model": "gpt-4o"}]}, _SERVICE)
    assert status == 400


def test_summarize_rejects_bad_slo() -> None:
    status, _ = handle("POST", "/summarize", {"calls": _CALLS, "slo_objective": 2.0}, _SERVICE)
    assert status == 400


def test_unknown_route() -> None:
    status, payload = handle("GET", "/nope", {}, _SERVICE)
    assert status == 404
    assert "error" in payload
