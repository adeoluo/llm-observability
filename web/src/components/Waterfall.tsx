import { formatDuration } from "../format";
import type { WaterfallLayout } from "../waterfall";
import { timeTicks } from "../waterfall";

export interface WaterfallProps {
  layout: WaterfallLayout;
  selectedId: string | null;
  onSelect: (spanId: string) => void;
}

const INDENT_PX = 14;

/** Where to draw a bar's duration label so it stays inside the track. */
function durationPlacement(offsetPct: number, widthPct: number): "after" | "inside" | "before" {
  if (offsetPct + widthPct <= 80) return "after";
  return widthPct >= 15 ? "inside" : "before";
}

export function Waterfall({ layout, selectedId, onSelect }: WaterfallProps) {
  const ticks = timeTicks(layout.totalMs);
  return (
    <div class="waterfall" role="tree">
      <div class="wf-row wf-axis">
        <div class="wf-label muted">Span</div>
        <div class="wf-track">
          {ticks.map((tick) => (
            <span key={tick.ms} class="wf-tick" style={{ left: `${tick.pct}%` }}>
              {formatDuration(tick.ms)}
            </span>
          ))}
        </div>
      </div>
      {layout.rows.map((row) => {
        const selected = row.span.spanId === selectedId;
        const status = row.span.status === "error" ? "error" : "ok";
        const placement = durationPlacement(row.offsetPct, row.widthPct);
        return (
          <div
            key={row.span.spanId}
            role="treeitem"
            aria-selected={selected}
            class={`wf-row clickable${selected ? " selected" : ""}`}
            onClick={() => onSelect(row.span.spanId)}
          >
            <div class="wf-label" style={{ paddingLeft: `${row.depth * INDENT_PX + 6}px` }}>
              <span class={`dot ${status}`} />
              <span class="wf-name">{row.span.name}</span>
            </div>
            <div class="wf-track">
              {ticks.map((tick) => (
                <span key={tick.ms} class="wf-grid" style={{ left: `${tick.pct}%` }} />
              ))}
              <div
                class={`wf-bar ${status} depth-${Math.min(row.depth, 3)}`}
                style={{ left: `${row.offsetPct}%`, width: `${row.widthPct}%` }}
                title={`${row.span.name}: ${formatDuration(row.durationMs)}`}
              />
              <span
                class={`wf-duration${placement === "inside" ? " inside" : ""}`}
                style={
                  placement === "after"
                    ? { left: `${row.offsetPct + row.widthPct + 0.5}%` }
                    : placement === "inside"
                      ? { right: `${100 - row.offsetPct - row.widthPct + 0.5}%` }
                      : { right: `${100 - row.offsetPct + 0.5}%` }
                }
              >
                {formatDuration(row.durationMs)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
