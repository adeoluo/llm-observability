import type { SpanRecord } from "./types";

/** One positioned bar in the waterfall. Offsets and widths are percentages of the trace. */
export interface WaterfallRow {
  span: SpanRecord;
  depth: number;
  /** Milliseconds from the start of the trace to the start of the span. */
  startMs: number;
  durationMs: number;
  /** Time not covered by any direct child span, in milliseconds. */
  selfMs: number;
  offsetPct: number;
  widthPct: number;
  childCount: number;
}

export interface WaterfallLayout {
  rows: WaterfallRow[];
  /** Trace start in seconds (the earliest span start). */
  traceStart: number;
  totalMs: number;
}

export interface LayoutOptions {
  /** Smallest bar width, so instant spans stay visible. */
  minWidthPct?: number;
}

function endOf(span: SpanRecord): number {
  return span.endTime === null ? span.startTime : Math.max(span.endTime, span.startTime);
}

function byStart(a: SpanRecord, b: SpanRecord): number {
  return a.startTime - b.startTime || a.name.localeCompare(b.name) || a.spanId.localeCompare(b.spanId);
}

/** Total time inside `[start, end]` covered by the union of the given intervals. */
export function coveredMs(start: number, end: number, intervals: Array<[number, number]>): number {
  const clipped = intervals
    .map(([s, e]): [number, number] => [Math.max(s, start), Math.min(e, end)])
    .filter(([s, e]) => e > s)
    .sort((a, b) => a[0] - b[0]);
  let total = 0;
  let curStart = Number.NaN;
  let curEnd = Number.NaN;
  for (const [s, e] of clipped) {
    if (Number.isNaN(curStart) || s > curEnd) {
      if (!Number.isNaN(curStart)) total += curEnd - curStart;
      curStart = s;
      curEnd = e;
    } else {
      curEnd = Math.max(curEnd, e);
    }
  }
  if (!Number.isNaN(curStart)) total += curEnd - curStart;
  return total * 1000;
}

/**
 * Lay spans out as a waterfall: depth-first by parent, children ordered by start time,
 * with each bar's offset and width proportional to its timing within the whole trace.
 * Spans whose parent is missing from the trace are treated as roots.
 */
export function layoutWaterfall(spans: SpanRecord[], options: LayoutOptions = {}): WaterfallLayout {
  const minWidthPct = options.minWidthPct ?? 0.4;
  if (spans.length === 0) {
    return { rows: [], traceStart: 0, totalMs: 0 };
  }
  const traceStart = Math.min(...spans.map((span) => span.startTime));
  const traceEnd = Math.max(...spans.map(endOf));
  const totalMs = (traceEnd - traceStart) * 1000;

  const ids = new Set(spans.map((span) => span.spanId));
  const children = new Map<string | null, SpanRecord[]>();
  for (const span of spans) {
    const parent = span.parentId !== null && ids.has(span.parentId) && span.parentId !== span.spanId
      ? span.parentId
      : null;
    const siblings = children.get(parent) ?? [];
    siblings.push(span);
    children.set(parent, siblings);
  }
  for (const siblings of children.values()) siblings.sort(byStart);

  const rows: WaterfallRow[] = [];
  const visited = new Set<string>();

  const place = (span: SpanRecord, depth: number): void => {
    if (visited.has(span.spanId)) return;
    visited.add(span.spanId);
    const kids = children.get(span.spanId) ?? [];
    const start = span.startTime;
    const end = endOf(span);
    const durationMs = (end - start) * 1000;
    const startMs = (start - traceStart) * 1000;
    let offsetPct = totalMs > 0 ? (startMs / totalMs) * 100 : 0;
    let widthPct = totalMs > 0 ? (durationMs / totalMs) * 100 : 100;
    widthPct = Math.min(100, Math.max(widthPct, minWidthPct));
    if (offsetPct + widthPct > 100) offsetPct = 100 - widthPct;
    const covered = coveredMs(start, end, kids.map((kid): [number, number] => [kid.startTime, endOf(kid)]));
    rows.push({
      span,
      depth,
      startMs,
      durationMs,
      selfMs: Math.max(0, durationMs - covered),
      offsetPct,
      widthPct,
      childCount: kids.length,
    });
    for (const kid of kids) place(kid, depth + 1);
  };

  for (const root of children.get(null) ?? []) place(root, 0);
  // Spans caught in a parent cycle are unreachable from any root; show them at top level.
  for (const span of [...spans].sort(byStart)) place(span, 0);

  return { rows, traceStart, totalMs };
}

export interface Tick {
  ms: number;
  pct: number;
}

/** A "nice" step (1, 2, or 5 times a power of ten) giving at most `maxTicks` intervals. */
export function niceStep(range: number, maxTicks: number): number {
  if (range <= 0 || maxTicks <= 0) return 1;
  const rough = range / maxTicks;
  const power = 10 ** Math.floor(Math.log10(rough));
  for (const factor of [1, 2, 5, 10]) {
    if (factor * power >= rough) return factor * power;
  }
  return 10 * power;
}

/** Axis ticks for a waterfall spanning `totalMs`, positioned as percentages. */
export function timeTicks(totalMs: number, maxTicks = 5): Tick[] {
  if (totalMs <= 0) return [{ ms: 0, pct: 0 }];
  const step = niceStep(totalMs, maxTicks);
  const ticks: Tick[] = [];
  for (let ms = 0; ms <= totalMs + step * 1e-9; ms += step) {
    ticks.push({ ms, pct: (ms / totalMs) * 100 });
  }
  return ticks;
}
