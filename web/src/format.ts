import type { AttributeValue, SpanRecord } from "./types";

export const ATTR_MODEL = "llm.model";
export const ATTR_INPUT_TOKENS = "llm.input_tokens";
export const ATTR_OUTPUT_TOKENS = "llm.output_tokens";
export const ATTR_COST = "llm.cost_usd";

/** Format milliseconds compactly: "850 us", "12.4 ms", "1.25 s", "2m 05s". */
export function formatDuration(ms: number): string {
  if (!Number.isFinite(ms)) return "n/a";
  const abs = Math.abs(ms);
  const sign = ms < 0 ? "-" : "";
  if (abs === 0) return "0 ms";
  if (abs < 1) return `${sign}${Math.round(abs * 1000)} us`;
  if (abs < 10) return `${sign}${abs.toFixed(2)} ms`;
  if (abs < 1000) return `${sign}${abs.toFixed(abs < 100 ? 1 : 0)} ms`;
  if (abs < 60_000) return `${sign}${(abs / 1000).toFixed(2)} s`;
  const minutes = Math.floor(abs / 60_000);
  const seconds = Math.round((abs % 60_000) / 1000);
  return `${sign}${minutes}m ${String(seconds).padStart(2, "0")}s`;
}

/** Format US dollars, keeping precision for the sub-cent costs typical of single calls. */
export function formatCost(usd: number): string {
  if (!Number.isFinite(usd)) return "n/a";
  if (usd === 0) return "$0.00";
  const abs = Math.abs(usd);
  if (abs < 0.01) return `$${usd.toFixed(5)}`;
  if (abs < 1) return `$${usd.toFixed(4)}`;
  return `$${usd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/** Format a token count: "950", "12.3k", "4.20M". */
export function formatTokens(count: number): string {
  if (!Number.isFinite(count)) return "n/a";
  const abs = Math.abs(count);
  if (abs < 1000) return String(Math.round(count));
  if (abs < 1_000_000) return `${(count / 1000).toFixed(abs < 10_000 ? 2 : 1)}k`;
  return `${(count / 1_000_000).toFixed(2)}M`;
}

/** Format a ratio in [0, 1] as a percentage. */
export function formatPercent(ratio: number, digits = 1): string {
  if (!Number.isFinite(ratio)) return "n/a";
  return `${(ratio * 100).toFixed(digits)}%`;
}

/** Format a collector timestamp (seconds since the epoch) as UTC "YYYY-MM-DD HH:MM:SS". */
export function formatTimestamp(seconds: number): string {
  if (!Number.isFinite(seconds)) return "n/a";
  return new Date(seconds * 1000).toISOString().slice(0, 19).replace("T", " ");
}

export function formatAttribute(value: AttributeValue): string {
  if (value === null) return "null";
  if (typeof value === "number" && !Number.isInteger(value)) {
    return String(Number(value.toPrecision(6)));
  }
  return String(value);
}

export interface LlmDetails {
  model: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  costUsd: number;
}

function numeric(value: AttributeValue | undefined): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

/** Extract the standard LLM-call attributes from a span, or null if it is not an LLM call. */
export function llmDetails(span: SpanRecord): LlmDetails | null {
  const model = span.attributes[ATTR_MODEL];
  if (model === undefined || model === null) return null;
  const inputTokens = numeric(span.attributes[ATTR_INPUT_TOKENS]);
  const outputTokens = numeric(span.attributes[ATTR_OUTPUT_TOKENS]);
  return {
    model: String(model),
    inputTokens,
    outputTokens,
    totalTokens: inputTokens + outputTokens,
    costUsd: numeric(span.attributes[ATTR_COST]),
  };
}

/** The error message recorded on a span, if any. */
export function spanError(span: SpanRecord): string | null {
  if (span.status !== "error") return null;
  const message = span.attributes["error.message"] ?? span.attributes["error.type"];
  return message === undefined || message === null ? "error" : String(message);
}
