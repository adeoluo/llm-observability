import { Fragment } from "preact";
import {
  formatAttribute,
  formatCost,
  formatDuration,
  formatTokens,
  llmDetails,
  spanError,
} from "../format";
import type { WaterfallRow } from "../waterfall";

export interface SpanPanelProps {
  row: WaterfallRow;
}

export function SpanPanel({ row }: SpanPanelProps) {
  const { span } = row;
  const llm = llmDetails(span);
  const error = spanError(span);
  const attributes = Object.entries(span.attributes).sort(([a], [b]) => a.localeCompare(b));
  return (
    <aside class="span-panel">
      <h2>{span.name}</h2>
      <p class="muted mono">{span.spanId}</p>
      {error !== null && <p class="error-box">{error}</p>}
      <dl class="kv">
        <dt>Status</dt>
        <dd>
          <span class={`pill ${span.status === "error" ? "error" : "ok"}`}>{span.status}</span>
        </dd>
        <dt>Latency</dt>
        <dd>{formatDuration(row.durationMs)}</dd>
        <dt>Self time</dt>
        <dd>{formatDuration(row.selfMs)}</dd>
        <dt>Starts at</dt>
        <dd>+{formatDuration(row.startMs)}</dd>
        <dt>Children</dt>
        <dd>{row.childCount}</dd>
      </dl>
      {llm !== null && (
        <>
          <h3>LLM call</h3>
          <dl class="kv">
            <dt>Model</dt>
            <dd>{llm.model}</dd>
            <dt>Input tokens</dt>
            <dd>{formatTokens(llm.inputTokens)}</dd>
            <dt>Output tokens</dt>
            <dd>{formatTokens(llm.outputTokens)}</dd>
            <dt>Total tokens</dt>
            <dd>{formatTokens(llm.totalTokens)}</dd>
            <dt>Cost</dt>
            <dd>{formatCost(llm.costUsd)}</dd>
          </dl>
        </>
      )}
      <h3>Attributes</h3>
      {attributes.length === 0 ? (
        <p class="muted">None</p>
      ) : (
        <dl class="kv mono">
          {attributes.map(([key, value]) => (
            <Fragment key={key}>
              <dt>{key}</dt>
              <dd>{formatAttribute(value)}</dd>
            </Fragment>
          ))}
        </dl>
      )}
      {span.events.length > 0 && (
        <>
          <h3>Events</h3>
          <ul class="events">
            {span.events.map((event, index) => (
              <li key={index}>
                <strong>{event.name}</strong>{" "}
                <span class="muted">
                  +{formatDuration((event.timestamp - span.startTime) * 1000)}
                </span>
                {Object.entries(event.attributes).map(([key, value]) => (
                  <span key={key} class="mono">
                    {" "}
                    {key}={formatAttribute(value)}
                  </span>
                ))}
              </li>
            ))}
          </ul>
        </>
      )}
    </aside>
  );
}
