export type TraceStatus = "ok" | "error";
export type SpanStatus = "ok" | "error" | "unset";

export type AttributeValue = string | number | boolean | null;

/** One row of the trace list (GET /api/traces). */
export interface TraceRow {
  traceId: string;
  name: string;
  /** Start of the trace, in seconds (the collector's clock). */
  startTime: number;
  durationMs: number;
  status: TraceStatus;
  models: string[];
  spanCount: number;
  llmCalls: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
  errors: number;
}

export interface TraceList {
  total: number;
  traces: TraceRow[];
}

export interface SpanEvent {
  timestamp: number;
  name: string;
  attributes: Record<string, AttributeValue>;
}

export interface SpanRecord {
  spanId: string;
  traceId: string;
  parentId: string | null;
  name: string;
  /** Seconds. */
  startTime: number;
  /** Seconds; null while the span is still open. */
  endTime: number | null;
  status: SpanStatus;
  attributes: Record<string, AttributeValue>;
  events: SpanEvent[];
}

/** A trace with all of its spans (GET /api/traces/{id}). */
export interface TraceDetail {
  summary: TraceRow;
  spans: SpanRecord[];
}

export interface ModelBreakdown {
  model: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

/** Aggregate metrics over every stored trace (GET /api/summary). */
export interface Summary {
  traces: number;
  totalCostUsd: number;
  totalTokens: number;
  errorRate: number;
  latencyP50Ms: number;
  latencyP95Ms: number;
  latencyP99Ms: number;
  byModel: ModelBreakdown[];
}

export interface TraceFilters {
  status?: TraceStatus;
  model?: string;
  minLatencyMs?: number;
}
