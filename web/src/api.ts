import type {
  AttributeValue,
  ModelBreakdown,
  SpanEvent,
  SpanRecord,
  SpanStatus,
  Summary,
  TraceDetail,
  TraceFilters,
  TraceList,
  TraceRow,
  TraceStatus,
} from "./types";

/** Raised when a response is not the shape the dashboard expects, or the request failed. */
export class ApiError extends Error {
  readonly status: number | undefined;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type JsonRecord = Record<string, unknown>;

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function record(value: unknown, where: string): JsonRecord {
  if (!isRecord(value)) {
    throw new ApiError(`${where}: expected an object`);
  }
  return value;
}

function num(obj: JsonRecord, key: string, where: string): number {
  const value = obj[key];
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new ApiError(`${where}.${key}: expected a number`);
  }
  return value;
}

function str(obj: JsonRecord, key: string, where: string): string {
  const value = obj[key];
  if (typeof value !== "string") {
    throw new ApiError(`${where}.${key}: expected a string`);
  }
  return value;
}

function list(obj: JsonRecord, key: string, where: string): unknown[] {
  const value = obj[key];
  if (!Array.isArray(value)) {
    throw new ApiError(`${where}.${key}: expected an array`);
  }
  return value;
}

function attributes(value: unknown, where: string): Record<string, AttributeValue> {
  if (value === undefined || value === null) {
    return {};
  }
  const obj = record(value, where);
  const out: Record<string, AttributeValue> = {};
  for (const [key, raw] of Object.entries(obj)) {
    if (
      raw === null ||
      typeof raw === "string" ||
      typeof raw === "number" ||
      typeof raw === "boolean"
    ) {
      out[key] = raw;
    } else {
      out[key] = JSON.stringify(raw);
    }
  }
  return out;
}

function traceStatus(value: string, where: string): TraceStatus {
  if (value === "ok" || value === "error") {
    return value;
  }
  throw new ApiError(`${where}.status: unknown status ${JSON.stringify(value)}`);
}

function spanStatus(value: string, where: string): SpanStatus {
  if (value === "ok" || value === "error" || value === "unset") {
    return value;
  }
  throw new ApiError(`${where}.status: unknown status ${JSON.stringify(value)}`);
}

export function parseTraceRow(value: unknown, where = "trace"): TraceRow {
  const obj = record(value, where);
  const models = list(obj, "models", where).map((model, index) => {
    if (typeof model !== "string") {
      throw new ApiError(`${where}.models[${index}]: expected a string`);
    }
    return model;
  });
  return {
    traceId: str(obj, "trace_id", where),
    name: str(obj, "name", where),
    startTime: num(obj, "start_time", where),
    durationMs: num(obj, "duration_ms", where),
    status: traceStatus(str(obj, "status", where), where),
    models,
    spanCount: num(obj, "span_count", where),
    llmCalls: num(obj, "llm_calls", where),
    inputTokens: num(obj, "input_tokens", where),
    outputTokens: num(obj, "output_tokens", where),
    totalTokens: num(obj, "total_tokens", where),
    costUsd: num(obj, "cost_usd", where),
    errors: num(obj, "errors", where),
  };
}

export function parseTraceList(value: unknown): TraceList {
  const obj = record(value, "response");
  return {
    total: num(obj, "total", "response"),
    traces: list(obj, "traces", "response").map((row, index) =>
      parseTraceRow(row, `traces[${index}]`),
    ),
  };
}

function parseEvent(value: unknown, where: string): SpanEvent {
  const obj = record(value, where);
  return {
    timestamp: num(obj, "timestamp", where),
    name: str(obj, "name", where),
    attributes: attributes(obj["attributes"], `${where}.attributes`),
  };
}

export function parseSpan(value: unknown, where = "span"): SpanRecord {
  const obj = record(value, where);
  const parent = obj["parent_id"];
  if (parent !== null && parent !== undefined && typeof parent !== "string") {
    throw new ApiError(`${where}.parent_id: expected a string or null`);
  }
  const end = obj["end_time"];
  if (end !== null && end !== undefined && (typeof end !== "number" || !Number.isFinite(end))) {
    throw new ApiError(`${where}.end_time: expected a number or null`);
  }
  const events = obj["events"] === undefined ? [] : list(obj, "events", where);
  return {
    spanId: str(obj, "span_id", where),
    traceId: str(obj, "trace_id", where),
    parentId: parent ?? null,
    name: str(obj, "name", where),
    startTime: num(obj, "start_time", where),
    endTime: end ?? null,
    status: spanStatus(str(obj, "status", where), where),
    attributes: attributes(obj["attributes"], `${where}.attributes`),
    events: events.map((event, index) => parseEvent(event, `${where}.events[${index}]`)),
  };
}

export function parseTraceDetail(value: unknown): TraceDetail {
  const obj = record(value, "response");
  return {
    summary: parseTraceRow(obj["summary"], "summary"),
    spans: list(obj, "spans", "response").map((span, index) => parseSpan(span, `spans[${index}]`)),
  };
}

function parseModel(value: unknown, where: string): ModelBreakdown {
  const obj = record(value, where);
  return {
    model: str(obj, "model", where),
    calls: num(obj, "calls", where),
    inputTokens: num(obj, "input_tokens", where),
    outputTokens: num(obj, "output_tokens", where),
    costUsd: num(obj, "cost_usd", where),
  };
}

export function parseSummary(value: unknown): Summary {
  const obj = record(value, "summary");
  return {
    traces: num(obj, "traces", "summary"),
    totalCostUsd: num(obj, "total_cost_usd", "summary"),
    totalTokens: num(obj, "total_tokens", "summary"),
    errorRate: num(obj, "error_rate", "summary"),
    latencyP50Ms: num(obj, "latency_p50_ms", "summary"),
    latencyP95Ms: num(obj, "latency_p95_ms", "summary"),
    latencyP99Ms: num(obj, "latency_p99_ms", "summary"),
    byModel: list(obj, "by_model", "summary").map((entry, index) =>
      parseModel(entry, `summary.by_model[${index}]`),
    ),
  };
}

/** Build the query string for GET /api/traces (empty filters are omitted). */
export function traceQuery(filters: TraceFilters, limit?: number): string {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.model) params.set("model", filters.model);
  if (filters.minLatencyMs !== undefined && Number.isFinite(filters.minLatencyMs)) {
    params.set("min_latency_ms", String(filters.minLatencyMs));
  }
  if (limit !== undefined) params.set("limit", String(limit));
  const text = params.toString();
  return text ? `?${text}` : "";
}

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export interface ApiClient {
  listTraces(filters: TraceFilters, limit?: number): Promise<TraceList>;
  getTrace(traceId: string): Promise<TraceDetail>;
  getSummary(): Promise<Summary>;
}

/** Create a client for the service's JSON API; `baseUrl` is "" when served by the service. */
export function createApiClient(fetchFn: FetchLike, baseUrl = ""): ApiClient {
  async function getJson(path: string): Promise<unknown> {
    let response: Response;
    try {
      response = await fetchFn(`${baseUrl}${path}`, { headers: { Accept: "application/json" } });
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      throw new ApiError(`request to ${path} failed: ${reason}`);
    }
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError(`${path} returned a non-JSON response`, response.status);
    }
    if (!response.ok) {
      const message =
        isRecord(body) && typeof body["error"] === "string"
          ? body["error"]
          : `HTTP ${response.status}`;
      throw new ApiError(message, response.status);
    }
    return body;
  }

  return {
    async listTraces(filters, limit) {
      return parseTraceList(await getJson(`/api/traces${traceQuery(filters, limit)}`));
    },
    async getTrace(traceId) {
      return parseTraceDetail(await getJson(`/api/traces/${encodeURIComponent(traceId)}`));
    },
    async getSummary() {
      return parseSummary(await getJson("/api/summary"));
    },
  };
}
