import { useMemo, useState } from "preact/hooks";
import type { ApiClient } from "../api";
import { formatCost, formatDuration, formatTimestamp, formatTokens } from "../format";
import { layoutWaterfall } from "../waterfall";
import { SpanPanel } from "./SpanPanel";
import { useAsync } from "./useAsync";
import { Waterfall } from "./Waterfall";

export interface TraceDetailPageProps {
  client: ApiClient;
  traceId: string;
}

export function TraceDetailPage({ client, traceId }: TraceDetailPageProps) {
  const detail = useAsync(() => client.getTrace(traceId), [traceId]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const layout = useMemo(
    () => (detail.kind === "ready" ? layoutWaterfall(detail.value.spans) : null),
    [detail],
  );

  if (detail.kind === "loading") return <p class="muted">Loading trace...</p>;
  if (detail.kind === "error") {
    return (
      <section>
        <p>
          <a href="#/traces">Back to traces</a>
        </p>
        <p class="error-box">Could not load trace: {detail.message}</p>
      </section>
    );
  }
  const { summary } = detail.value;
  const rows = layout?.rows ?? [];
  const selected =
    rows.find((row) => row.span.spanId === selectedId) ??
    rows.find((row) => row.span.status === "error" && row.childCount === 0) ??
    rows[0];

  return (
    <section>
      <p>
        <a href="#/traces">Back to traces</a>
      </p>
      <div class="page-head">
        <h1>
          {summary.name} <span class="muted mono">{summary.traceId}</span>
        </h1>
        <span class={`pill ${summary.status}`}>{summary.status === "ok" ? "OK" : "Error"}</span>
      </div>
      <div class="stats compact">
        <Stat label="Started (UTC)" value={formatTimestamp(summary.startTime)} />
        <Stat label="Latency" value={formatDuration(summary.durationMs)} />
        <Stat label="Spans" value={String(summary.spanCount)} />
        <Stat label="LLM calls" value={String(summary.llmCalls)} />
        <Stat
          label="Tokens (in / out)"
          value={`${formatTokens(summary.inputTokens)} / ${formatTokens(summary.outputTokens)}`}
        />
        <Stat label="Cost" value={formatCost(summary.costUsd)} />
        <Stat label="Errors" value={String(summary.errors)} />
      </div>
      <div class="detail">
        {layout && (
          <Waterfall
            layout={layout}
            selectedId={selected?.span.spanId ?? null}
            onSelect={setSelectedId}
          />
        )}
        {selected && <SpanPanel row={selected} />}
      </div>
    </section>
  );
}

export function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div class={`stat${tone ? ` ${tone}` : ""}`}>
      <div class="stat-label">{label}</div>
      <div class="stat-value">{value}</div>
    </div>
  );
}
