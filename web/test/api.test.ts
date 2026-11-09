import { describe, expect, it, vi } from "vitest";
import {
  ApiError,
  createApiClient,
  parseSpan,
  parseSummary,
  parseTraceDetail,
  parseTraceList,
  traceQuery,
} from "../src/api";

const row = {
  trace_id: "trace-0001",
  name: "agent.run",
  start_time: 1793000000.5,
  duration_ms: 1234.5,
  status: "error",
  models: ["gpt-6.1-sol"],
  span_count: 4,
  llm_calls: 2,
  input_tokens: 800,
  output_tokens: 90,
  total_tokens: 890,
  cost_usd: 0.0029,
  errors: 1,
};

const rawSpan = {
  name: "llm.call",
  span_id: "trace-0001-s2",
  trace_id: "trace-0001",
  parent_id: "trace-0001-s1",
  start_time: 1793000000.6,
  end_time: 1793000001.1,
  status: "error",
  attributes: { "llm.model": "gpt-6.1-sol", "llm.input_tokens": 400, nested: { a: 1 } },
  events: [{ timestamp: 1793000001.1, name: "exception", attributes: { type: "timeout" } }],
};

const summary = {
  traces: 3,
  total_cost_usd: 0.01,
  total_tokens: 2000,
  error_rate: 0.3333,
  latency_p50_ms: 900,
  latency_p95_ms: 1500,
  latency_p99_ms: 1600,
  by_model: [{ model: "gpt-6.1-sol", calls: 3, input_tokens: 1500, output_tokens: 500, cost_usd: 0.01 }],
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("parsers", () => {
  it("maps snake_case trace rows to camelCase", () => {
    const list = parseTraceList({ total: 1, traces: [row] });
    expect(list.total).toBe(1);
    expect(list.traces[0]).toMatchObject({
      traceId: "trace-0001",
      durationMs: 1234.5,
      status: "error",
      totalTokens: 890,
      costUsd: 0.0029,
    });
  });

  it("parses spans, stringifying non-scalar attributes", () => {
    const parsed = parseSpan(rawSpan);
    expect(parsed.parentId).toBe("trace-0001-s1");
    expect(parsed.endTime).toBe(1793000001.1);
    expect(parsed.attributes["nested"]).toBe('{"a":1}');
    expect(parsed.events[0]?.attributes).toEqual({ type: "timeout" });
  });

  it("defaults missing optional span fields", () => {
    const { events: _events, parent_id: _parent, attributes: _attrs, ...minimal } = rawSpan;
    const parsed = parseSpan({ ...minimal, end_time: null });
    expect(parsed.parentId).toBeNull();
    expect(parsed.endTime).toBeNull();
    expect(parsed.attributes).toEqual({});
    expect(parsed.events).toEqual([]);
  });

  it("parses trace details and summaries", () => {
    const detail = parseTraceDetail({ summary: row, spans: [rawSpan] });
    expect(detail.summary.traceId).toBe("trace-0001");
    expect(detail.spans).toHaveLength(1);
    const parsed = parseSummary(summary);
    expect(parsed.latencyP95Ms).toBe(1500);
    expect(parsed.byModel[0]).toEqual({
      model: "gpt-6.1-sol",
      calls: 3,
      inputTokens: 1500,
      outputTokens: 500,
      costUsd: 0.01,
    });
  });

  it.each([
    ["not an object", () => parseTraceList([]), /expected an object/],
    ["missing number", () => parseTraceList({ traces: [] }), /response\.total: expected a number/],
    ["bad status", () => parseTraceList({ total: 1, traces: [{ ...row, status: "weird" }] }), /unknown status/],
    ["bad model", () => parseTraceList({ total: 1, traces: [{ ...row, models: [1] }] }), /models\[0\]/],
    ["bad parent", () => parseSpan({ ...rawSpan, parent_id: 5 }), /parent_id/],
    ["bad end", () => parseSpan({ ...rawSpan, end_time: "soon" }), /end_time/],
    ["bad span status", () => parseSpan({ ...rawSpan, status: "done" }), /unknown status/],
    ["bad events", () => parseSpan({ ...rawSpan, events: {} }), /expected an array/],
  ])("rejects malformed input: %s", (_label, run, message) => {
    expect(run).toThrow(ApiError);
    expect(run).toThrow(message);
  });
});

describe("traceQuery", () => {
  it("omits empty filters", () => {
    expect(traceQuery({})).toBe("");
  });

  it("encodes every filter and the limit", () => {
    expect(traceQuery({ status: "error", model: "gpt-6.1-sol mini", minLatencyMs: 500 }, 50)).toBe(
      "?status=error&model=gpt-6.1-sol+mini&min_latency_ms=500&limit=50",
    );
  });
});

describe("createApiClient", () => {
  it("requests the expected URLs and parses responses", async () => {
    const fetchFn = vi.fn(async (input: string) => {
      if (input.startsWith("/base/api/traces/")) return jsonResponse({ summary: row, spans: [rawSpan] });
      if (input.startsWith("/base/api/traces")) return jsonResponse({ total: 1, traces: [row] });
      return jsonResponse(summary);
    });
    const client = createApiClient(fetchFn, "/base");
    expect((await client.listTraces({ status: "ok" }, 10)).total).toBe(1);
    expect((await client.getTrace("a/b")).spans).toHaveLength(1);
    expect((await client.getSummary()).traces).toBe(3);
    expect(fetchFn.mock.calls.map((call) => call[0])).toEqual([
      "/base/api/traces?status=ok&limit=10",
      "/base/api/traces/a%2Fb",
      "/base/api/summary",
    ]);
  });

  it("surfaces the service's error message and status", async () => {
    const client = createApiClient(async () => jsonResponse({ error: "trace 'x' not found" }, 404));
    await expect(client.getTrace("x")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "trace 'x' not found",
    });
  });

  it("falls back to the HTTP status when the error body has no message", async () => {
    const client = createApiClient(async () => jsonResponse({}, 500));
    await expect(client.getSummary()).rejects.toThrow("HTTP 500");
  });

  it("reports network failures and non-JSON bodies", async () => {
    const offline = createApiClient(async () => {
      throw new TypeError("connection refused");
    });
    await expect(offline.getSummary()).rejects.toThrow(/failed: connection refused/);
    const html = createApiClient(async () => new Response("<html>", { status: 502 }));
    await expect(html.getSummary()).rejects.toMatchObject({ status: 502 });
  });
});
