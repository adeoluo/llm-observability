import type { ApiClient } from "../api";
import { formatCost, formatDuration, formatPercent, formatTokens } from "../format";
import { histogram } from "../stats";
import { BarChart } from "./charts";
import { Stat } from "./TraceDetailPage";
import { useAsync } from "./useAsync";

export interface SummaryPageProps {
  client: ApiClient;
}

const HISTOGRAM_SAMPLE = 5000;

function shortDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
}

export function SummaryPage({ client }: SummaryPageProps) {
  const data = useAsync(
    () => Promise.all([client.getSummary(), client.listTraces({}, HISTOGRAM_SAMPLE)]),
    [],
  );
  if (data.kind === "loading") return <p class="muted">Loading summary...</p>;
  if (data.kind === "error") return <p class="error-box">Could not load summary: {data.message}</p>;
  const [summary, list] = data.value;
  if (summary.traces === 0) {
    return (
      <section>
        <h1>Summary</h1>
        <p class="muted">
          No traces yet. POST traces to /api/traces or start the service with --demo-traces 200.
        </p>
      </section>
    );
  }
  const errors = list.traces.filter((row) => row.status === "error").length;
  const buckets = histogram(
    list.traces.map((row) => row.durationMs),
    10,
  ).map((bucket) => ({ label: shortDuration(bucket.start), value: bucket.count }));
  const percentiles = [
    { label: "p50", value: summary.latencyP50Ms },
    { label: "p95", value: summary.latencyP95Ms },
    { label: "p99", value: summary.latencyP99Ms },
  ];
  const costByModel = summary.byModel.map((entry) => ({ label: entry.model, value: entry.costUsd }));
  const tokensByModel = summary.byModel.map((entry) => ({
    label: entry.model,
    value: entry.inputTokens + entry.outputTokens,
  }));

  return (
    <section>
      <div class="page-head">
        <h1>Summary</h1>
        <span class="muted">across {summary.traces} stored traces</span>
      </div>
      <div class="stats">
        <Stat label="Traces" value={String(summary.traces)} />
        <Stat label="Total cost" value={formatCost(summary.totalCostUsd)} />
        <Stat label="Total tokens" value={formatTokens(summary.totalTokens)} />
        <Stat
          label="Error rate"
          value={formatPercent(summary.errorRate)}
          tone={summary.errorRate > 0.05 ? "warn" : ""}
        />
        <Stat label="Latency p50" value={formatDuration(summary.latencyP50Ms)} />
        <Stat label="Latency p95" value={formatDuration(summary.latencyP95Ms)} />
        <Stat label="Latency p99" value={formatDuration(summary.latencyP99Ms)} />
      </div>
      <div class="charts">
        <figure class="card">
          <figcaption>Latency percentiles</figcaption>
          <BarChart data={percentiles} format={shortDuration} title="Latency percentiles" />
        </figure>
        <figure class="card">
          <figcaption>
            Latency distribution ({list.traces.length} traces, {errors} with errors)
          </figcaption>
          <BarChart
            data={buckets}
            format={(value) => String(Math.round(value))}
            title="Latency histogram"
            color="#0ea5e9"
          />
        </figure>
        <figure class="card">
          <figcaption>Cost by model</figcaption>
          <BarChart data={costByModel} format={formatCost} title="Cost by model" color="#10b981" />
        </figure>
        <figure class="card">
          <figcaption>Tokens by model</figcaption>
          <BarChart
            data={tokensByModel}
            format={formatTokens}
            title="Tokens by model"
            color="#f59e0b"
          />
        </figure>
      </div>
      <table class="trace-table">
        <thead>
          <tr>
            <th>Model</th>
            <th class="num">Calls</th>
            <th class="num">Input tokens</th>
            <th class="num">Output tokens</th>
            <th class="num">Cost</th>
          </tr>
        </thead>
        <tbody>
          {summary.byModel.map((entry) => (
            <tr key={entry.model}>
              <td>{entry.model}</td>
              <td class="num">{entry.calls}</td>
              <td class="num">{formatTokens(entry.inputTokens)}</td>
              <td class="num">{formatTokens(entry.outputTokens)}</td>
              <td class="num">{formatCost(entry.costUsd)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
