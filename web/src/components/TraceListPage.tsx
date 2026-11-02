import { useState } from "preact/hooks";
import type { ApiClient } from "../api";
import { formatCost, formatDuration, formatTimestamp, formatTokens } from "../format";
import type { TraceFilters, TraceList } from "../types";
import { navigate } from "./App";
import { useAsync } from "./useAsync";

export interface TraceListPageProps {
  client: ApiClient;
  filters: TraceFilters;
}

const PAGE_LIMIT = 200;

export function TraceListPage({ client, filters }: TraceListPageProps) {
  const query = JSON.stringify(filters);
  const list = useAsync<TraceList>(() => client.listTraces(filters, PAGE_LIMIT), [query]);
  const models = useAsync(
    async () => (await client.getSummary()).byModel.map((entry) => entry.model),
    [],
  );
  const [latencyText, setLatencyText] = useState(
    filters.minLatencyMs === undefined ? "" : String(filters.minLatencyMs),
  );

  const update = (next: TraceFilters) => navigate({ page: "traces", filters: next });

  const setStatus = (value: string) => {
    const next: TraceFilters = { ...filters };
    if (value === "ok" || value === "error") next.status = value;
    else delete next.status;
    update(next);
  };
  const setModel = (value: string) => {
    const next: TraceFilters = { ...filters };
    if (value) next.model = value;
    else delete next.model;
    update(next);
  };
  const applyLatency = (event: Event) => {
    event.preventDefault();
    const next: TraceFilters = { ...filters };
    const value = Number(latencyText);
    if (latencyText.trim() !== "" && Number.isFinite(value) && value >= 0) next.minLatencyMs = value;
    else delete next.minLatencyMs;
    update(next);
  };

  return (
    <section>
      <div class="page-head">
        <h1>Traces</h1>
        {list.kind === "ready" && (
          <span class="muted">
            {list.value.total === list.value.traces.length
              ? `${list.value.total} traces`
              : `showing ${list.value.traces.length} of ${list.value.total} traces`}
          </span>
        )}
      </div>
      <form class="filters" onSubmit={applyLatency}>
        <label>
          Status
          <select
            value={filters.status ?? ""}
            onChange={(event) => setStatus(event.currentTarget.value)}
          >
            <option value="">All</option>
            <option value="ok">OK</option>
            <option value="error">Error</option>
          </select>
        </label>
        <label>
          Model
          <select value={filters.model ?? ""} onChange={(event) => setModel(event.currentTarget.value)}>
            <option value="">All</option>
            {models.kind === "ready" &&
              models.value.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
          </select>
        </label>
        <label>
          Min latency (ms)
          <input
            type="number"
            min="0"
            step="any"
            placeholder="0"
            value={latencyText}
            onInput={(event) => setLatencyText(event.currentTarget.value)}
          />
        </label>
        <button type="submit">Apply</button>
        {(filters.status || filters.model || filters.minLatencyMs !== undefined) && (
          <button
            type="button"
            class="secondary"
            onClick={() => {
              setLatencyText("");
              update({});
            }}
          >
            Clear
          </button>
        )}
      </form>
      {list.kind === "loading" && <p class="muted">Loading traces...</p>}
      {list.kind === "error" && <p class="error-box">Could not load traces: {list.message}</p>}
      {list.kind === "ready" && list.value.traces.length === 0 && (
        <p class="muted">No traces match these filters.</p>
      )}
      {list.kind === "ready" && list.value.traces.length > 0 && (
        <table class="trace-table">
          <thead>
            <tr>
              <th>Trace</th>
              <th>Root span</th>
              <th>Started (UTC)</th>
              <th>Status</th>
              <th>Models</th>
              <th class="num">Spans</th>
              <th class="num">Tokens</th>
              <th class="num">Cost</th>
              <th class="num">Latency</th>
            </tr>
          </thead>
          <tbody>
            {list.value.traces.map((row) => (
              <tr
                key={row.traceId}
                class="clickable"
                onClick={() => navigate({ page: "trace", traceId: row.traceId })}
              >
                <td>
                  <a href={`#/trace/${encodeURIComponent(row.traceId)}`}>{row.traceId}</a>
                </td>
                <td>{row.name}</td>
                <td class="muted">{formatTimestamp(row.startTime)}</td>
                <td>
                  <span class={`pill ${row.status}`}>{row.status === "ok" ? "OK" : "Error"}</span>
                </td>
                <td>{row.models.join(", ")}</td>
                <td class="num">{row.spanCount}</td>
                <td class="num">{formatTokens(row.totalTokens)}</td>
                <td class="num">{formatCost(row.costUsd)}</td>
                <td class="num">{formatDuration(row.durationMs)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
