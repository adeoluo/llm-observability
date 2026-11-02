"""The HTTP service (collector and JSON API) built on the standard library.

The service ingests a batch of LLM-call records, builds traces from them with the
real tracing primitives, and returns an aggregate summary (cost, tokens, error
rate, and latency percentiles) plus an optional latency SLO evaluation. It also
collects full traces into an in-memory store, serves read-only JSON views of them
for the TypeScript dashboard, and serves the built dashboard itself under ``/ui``.
A pure handler is separated from the socket binding for testing.

Endpoints
---------
``GET  /health``           liveness and known model prices.
``POST /summarize``        body ``{"calls": [...], "slo_threshold_ms"?, "slo_objective"?}``;
                           returns the batch summary and, when a threshold is given, the SLO.
``POST /api/traces``       body ``{"traces": [<trace JSON>, ...]}``; stores the traces.
``GET  /api/traces``       trace list; query ``status``, ``model``, ``min_latency_ms``, ``limit``.
``GET  /api/traces/{id}``  one trace with its summary and all spans.
``GET  /api/summary``      totals, latency percentiles, error rate, and per-model breakdown.
``GET  /ui/``              the dashboard (static files from the built ``web/dist``).
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from llm_observability.analysis import summarize_batch
from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace
from llm_observability.cost import PriceList
from llm_observability.exporters import trace_from_dict
from llm_observability.metrics import record_llm_call
from llm_observability.observability import ServiceMetrics
from llm_observability.slo import evaluate_slo
from llm_observability.store import (
    TraceFilter,
    TraceStore,
    list_traces,
    store_summary,
    trace_detail,
)

JsonObject = dict[str, Any]
_MAX_CALLS = 10000
_MAX_INGEST_TRACES = 1000
_TRACES_PREFIX = "/api/traces/"
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
    ".json": "application/json",
    ".map": "application/json",
}


@dataclass(frozen=True)
class ObservabilityService:
    """Builds traces from call records and computes metrics and SLOs."""

    prices: PriceList = field(default_factory=PriceList)
    metrics: ServiceMetrics = field(default_factory=ServiceMetrics)
    store: TraceStore = field(default_factory=TraceStore)

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


def _parse_filter(query: Mapping[str, list[str]]) -> TraceFilter:
    def first(name: str) -> str | None:
        values = query.get(name)
        return values[0] if values and values[0] != "" else None

    status = first("status")
    if status is not None and status not in ("ok", "error"):
        raise ValueError("'status' must be 'ok' or 'error'")
    min_latency = first("min_latency_ms")
    min_latency_ms = float(min_latency) if min_latency is not None else None
    if min_latency_ms is not None and min_latency_ms < 0:
        raise ValueError("'min_latency_ms' must be non-negative")
    limit_text = first("limit")
    limit = int(limit_text) if limit_text is not None else 500
    if not 1 <= limit <= 5000:
        raise ValueError("'limit' must be between 1 and 5000")
    return TraceFilter(
        status=status, model=first("model"), min_latency_ms=min_latency_ms, limit=limit
    )


def _ingest_traces(body: Mapping[str, Any], service: ObservabilityService) -> JsonObject:
    items = body.get("traces")
    if not isinstance(items, list) or not items:
        raise ValueError("'traces' must be a non-empty list of trace objects")
    if len(items) > _MAX_INGEST_TRACES:
        raise ValueError(f"'traces' exceeds {_MAX_INGEST_TRACES} traces")
    traces = []
    for index, item in enumerate(items):
        if not isinstance(item, dict) or not isinstance(item.get("spans"), list):
            raise ValueError(f"trace {index} must be an object with 'trace_id' and 'spans'")
        traces.append(trace_from_dict(item))
    service.store.extend(traces)
    return {"ingested": len(traces), "stored": len(service.store)}


def _route_label(method: str, path: str) -> str:
    if path.startswith(_TRACES_PREFIX):
        return f"{method} {_TRACES_PREFIX}{{id}}"
    return f"{method} {path}"


def _route(
    method: str,
    path: str,
    query: Mapping[str, list[str]],
    body: Mapping[str, Any],
    service: ObservabilityService,
) -> tuple[int, JsonObject]:
    if method == "GET" and path == "/health":
        return 200, {"status": "ok", "models": service.prices.model_names()}
    if method == "POST" and path == "/summarize":
        try:
            calls, threshold, objective = _validate_summarize(body)
        except (ValueError, KeyError, TypeError) as error:
            return 400, {"error": str(error)}
        return 200, service.summarize(calls, slo_threshold_ms=threshold, slo_objective=objective)
    if method == "GET" and path == "/api/traces":
        try:
            criteria = _parse_filter(query)
        except ValueError as error:
            return 400, {"error": str(error)}
        return 200, list_traces(service.store, criteria)
    if method == "POST" and path == "/api/traces":
        try:
            return 201, _ingest_traces(body, service)
        except (ValueError, KeyError, TypeError) as error:
            return 400, {"error": str(error)}
    if method == "GET" and path.startswith(_TRACES_PREFIX):
        trace_id = unquote(path[len(_TRACES_PREFIX) :])
        trace = service.store.get(trace_id)
        if trace is None:
            return 404, {"error": f"trace {trace_id!r} not found"}
        return 200, trace_detail(trace)
    if method == "GET" and path == "/api/summary":
        return 200, store_summary(service.store)
    return 404, {"error": f"no route for {method} {path}"}


def handle(
    method: str, path: str, body: Mapping[str, Any], service: ObservabilityService
) -> tuple[int, JsonObject]:
    """Route a request, recording per-route metrics, and return status and payload."""

    parts = urlsplit(path)
    route_path = parts.path
    if method == "GET" and route_path == "/ready":
        return 200, {"status": "ready"}
    start = time.perf_counter()
    status, payload = _route(method, route_path, parse_qs(parts.query), body, service)
    service.metrics.observe(
        _route_label(method, route_path),
        (time.perf_counter() - start) * 1000.0,
        error=status >= 400,
    )
    return status, payload


def resolve_ui_file(ui_dir: Path, request_path: str) -> Path | None:
    """Map a ``/ui/...`` request path to a file inside ``ui_dir``.

    Returns ``index.html`` for the dashboard root and ``None`` for anything that is not
    an existing file inside ``ui_dir`` (including attempts to escape it with ``..``).
    """
    path = urlsplit(request_path).path
    if path != "/ui" and not path.startswith("/ui/"):
        return None
    relative = unquote(path[len("/ui") :]).lstrip("/") or "index.html"
    root = ui_dir.resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root) or not candidate.is_file():
        return None
    return candidate


def content_type_for(path: Path) -> str:
    """Return the Content-Type for a static dashboard file."""
    return _CONTENT_TYPES.get(path.suffix.lower(), "application/octet-stream")


def default_ui_dir() -> Path:
    """Locate the built dashboard: ``./web/dist``, else the source checkout's ``web/dist``."""
    local = Path.cwd() / "web" / "dist"
    if local.is_dir():
        return local
    return Path(__file__).resolve().parents[2] / "web" / "dist"


class _Handler(BaseHTTPRequestHandler):  # pragma: no cover - exercised over sockets
    service: ObservabilityService
    ui_dir: Path

    def _respond(self, status: int, payload: JsonObject) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_ui(self) -> None:
        if urlsplit(self.path).path == "/ui":
            self.send_response(301)
            self.send_header("Location", "/ui/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        target = resolve_ui_file(self.ui_dir, self.path)
        if target is None:
            message = "not found"
            if not (self.ui_dir / "index.html").is_file():
                message = "dashboard not built: run 'npm ci && npm run build' in web/"
            self._respond(404, {"error": message})
            return
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type_for(target))
        self.send_header("Content-Length", str(len(data)))
        cache = "no-cache" if target.name == "index.html" else "public, max-age=31536000"
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/ui" or path.startswith("/ui/"):
            self._serve_ui()
            return
        if path == "/":
            self.send_response(302)
            self.send_header("Location", "/ui/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/metrics":
            body = self.service.metrics.render_prometheus().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
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
        if not isinstance(body, dict):
            self._respond(400, {"error": "request body must be a JSON object"})
            return
        status, payload = handle("POST", self.path, body, self.service)
        self._respond(status, payload)

    def log_message(self, *_: Any) -> None:
        return


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    demo_traces: int = 0,
    ui_dir: Path | None = None,
) -> None:  # pragma: no cover
    """Start the HTTP service (blocking), optionally preloaded with sample traces."""

    service = ObservabilityService()
    if demo_traces > 0:
        from llm_observability.demo import generate_sample_traces

        service.store.extend(generate_sample_traces(demo_traces))
    static_dir = ui_dir if ui_dir is not None else default_ui_dir()
    handler = type("_BoundHandler", (_Handler,), {"service": service, "ui_dir": static_dir})
    server = ThreadingHTTPServer((host, port), handler)
    print(f"llm-observability service listening on http://{host}:{port}")
    print(f"dashboard: http://{host}:{port}/ui/ (static files from {static_dir})")
    server.serve_forever()
