"""A dependency-free HTTP service exposing the observability platform.

The service ingests a batch of LLM-call records, builds traces from them with the
real tracing primitives, and returns an aggregate summary (cost, tokens, error
rate, and latency percentiles) plus an optional latency SLO evaluation. A pure
handler is separated from the socket binding for testing.

Endpoints
---------
``GET  /health``    liveness and known model prices.
``POST /summarize`` body ``{"calls": [...], "slo_threshold_ms"?, "slo_objective"?}``;
                    returns the batch summary and, when a threshold is given, the SLO.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from llm_observability.analysis import summarize_batch
from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace
from llm_observability.cost import PriceList
from llm_observability.metrics import record_llm_call
from llm_observability.slo import evaluate_slo

JsonObject = dict[str, Any]
_MAX_CALLS = 10000


@dataclass(frozen=True)
class ObservabilityService:
    """Builds traces from call records and computes metrics and SLOs."""

    prices: PriceList = field(default_factory=PriceList)

    def _trace_from_call(self, index: int, call: Mapping[str, Any]) -> Trace:
        latency_ms = float(call["latency_ms"])
        span = Span(
            name="llm.call",
            span_id=f"span-{index}",
            trace_id=f"trace-{index}",
            start_time=0.0,
            end_time=latency_ms / 1000.0,
        )
        record_llm_call(
            span,
            model=str(call["model"]),
            input_tokens=int(call["input_tokens"]),
            output_tokens=int(call["output_tokens"]),
            prices=self.prices,
        )
        span.status = SpanStatus.ERROR if bool(call.get("error", False)) else SpanStatus.OK
        return Trace(span.trace_id, [span])

    def summarize(
        self,
        calls: Sequence[Mapping[str, Any]],
        *,
        slo_threshold_ms: float | None,
        slo_objective: float,
    ) -> JsonObject:
        traces = [self._trace_from_call(index, call) for index, call in enumerate(calls)]
        summary = summarize_batch(traces)
        payload: JsonObject = {
            "traces": summary.num_traces,
            "total_cost_usd": round(summary.total_cost_usd, 6),
            "total_tokens": summary.total_tokens,
            "error_rate": round(summary.error_rate, 4),
            "latency_p50_ms": round(summary.latency_p50_ms, 3),
            "latency_p95_ms": round(summary.latency_p95_ms, 3),
            "latency_p99_ms": round(summary.latency_p99_ms, 3),
        }
        if slo_threshold_ms is not None:
            report = evaluate_slo(traces, threshold_ms=slo_threshold_ms, objective=slo_objective)
            payload["slo"] = {
                "threshold_ms": report.threshold_ms,
                "objective": report.objective,
                "compliance": round(report.compliance, 4),
                "met": report.met,
                "error_budget_remaining": round(report.error_budget_remaining, 4),
            }
        return payload


def _validate_summarize(
    body: Mapping[str, Any],
) -> tuple[list[Mapping[str, Any]], float | None, float]:
    calls = body.get("calls")
    if not isinstance(calls, list) or not calls:
        raise ValueError("'calls' must be a non-empty list of call records")
    if len(calls) > _MAX_CALLS:
        raise ValueError(f"'calls' exceeds {_MAX_CALLS} records")
    required = ("model", "input_tokens", "output_tokens", "latency_ms")
    for index, call in enumerate(calls):
        if not isinstance(call, Mapping) or any(key not in call for key in required):
            raise ValueError(f"call {index} must have {', '.join(required)}")
    threshold = body.get("slo_threshold_ms")
    if threshold is not None and (not isinstance(threshold, int | float) or threshold <= 0):
        raise ValueError("'slo_threshold_ms' must be a positive number")
    objective = body.get("slo_objective", 0.95)
    if not isinstance(objective, int | float) or not 0.0 < objective <= 1.0:
        raise ValueError("'slo_objective' must be in (0, 1]")
    return calls, (float(threshold) if threshold is not None else None), float(objective)


def handle(
    method: str, path: str, body: Mapping[str, Any], service: ObservabilityService
) -> tuple[int, JsonObject]:
    """Pure request handler: route a request to a status code and payload."""

    if method == "GET" and path == "/health":
        return 200, {"status": "ok", "models": service.prices.model_names()}
    if method == "POST" and path == "/summarize":
        try:
            calls, threshold, objective = _validate_summarize(body)
        except (ValueError, KeyError, TypeError) as error:
            return 400, {"error": str(error)}
        return 200, service.summarize(calls, slo_threshold_ms=threshold, slo_objective=objective)
    return 404, {"error": f"no route for {method} {path}"}


class _Handler(BaseHTTPRequestHandler):  # pragma: no cover - exercised over sockets
    service: ObservabilityService

    def _respond(self, status: int, payload: JsonObject) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        status, payload = handle("GET", self.path, {}, self.service)
        self._respond(status, payload)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            self._respond(400, {"error": "request body is not valid JSON"})
            return
        status, payload = handle("POST", self.path, body, self.service)
        self._respond(status, payload)

    def log_message(self, *_: Any) -> None:
        return


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:  # pragma: no cover
    """Start the HTTP service (blocking)."""

    handler = type("_BoundHandler", (_Handler,), {"service": ObservabilityService()})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"llm-observability service listening on http://{host}:{port}")
    server.serve_forever()
