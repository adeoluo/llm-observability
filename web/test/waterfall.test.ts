import { describe, expect, it } from "vitest";
import { coveredMs, layoutWaterfall, niceStep, timeTicks } from "../src/waterfall";
import { span } from "./fixtures";

describe("layoutWaterfall", () => {
  it("returns an empty layout for no spans", () => {
    expect(layoutWaterfall([])).toEqual({ rows: [], traceStart: 0, totalMs: 0 });
  });

  it("orders rows depth first with children sorted by start time", () => {
    const spans = [
      span("late-child", "root", 100.6, 100.9),
      span("root", null, 100, 101),
      span("early-child", "root", 100.1, 100.5),
      span("grandchild", "early-child", 100.2, 100.3),
    ];
    const layout = layoutWaterfall(spans);
    expect(layout.rows.map((row) => [row.span.spanId, row.depth])).toEqual([
      ["root", 0],
      ["early-child", 1],
      ["grandchild", 2],
      ["late-child", 1],
    ]);
    expect(layout.traceStart).toBe(100);
    expect(layout.totalMs).toBeCloseTo(1000);
  });

  it("makes offsets and widths proportional to timing", () => {
    const layout = layoutWaterfall([
      span("root", null, 10, 12),
      span("child", "root", 10.5, 11),
    ]);
    const child = layout.rows[1]!;
    expect(child.startMs).toBeCloseTo(500);
    expect(child.durationMs).toBeCloseTo(500);
    expect(child.offsetPct).toBeCloseTo(25);
    expect(child.widthPct).toBeCloseTo(25);
    expect(layout.rows[0]!.widthPct).toBeCloseTo(100);
  });

  it("computes self time from the union of child intervals", () => {
    const layout = layoutWaterfall([
      span("root", null, 0, 1),
      span("a", "root", 0.1, 0.4),
      span("b", "root", 0.3, 0.5),
    ]);
    const root = layout.rows[0]!;
    expect(root.childCount).toBe(2);
    expect(root.selfMs).toBeCloseTo(600);
  });

  it("keeps instant spans visible and inside the track", () => {
    const layout = layoutWaterfall(
      [span("root", null, 0, 1), span("instant", "root", 1, 1)],
      { minWidthPct: 2 },
    );
    const instant = layout.rows[1]!;
    expect(instant.widthPct).toBe(2);
    expect(instant.offsetPct + instant.widthPct).toBeCloseTo(100);
  });

  it("treats open spans as zero length and orphans as roots", () => {
    const layout = layoutWaterfall([
      span("root", null, 0, 2),
      span("open", "root", 1, null),
      span("orphan", "missing", 0.5, 1),
    ]);
    const byId = new Map(layout.rows.map((row) => [row.span.spanId, row]));
    expect(byId.get("open")!.durationMs).toBe(0);
    expect(byId.get("orphan")!.depth).toBe(0);
  });

  it("gives a full-width bar when the whole trace has zero duration", () => {
    const layout = layoutWaterfall([span("only", null, 5, 5)]);
    expect(layout.totalMs).toBe(0);
    expect(layout.rows[0]!.widthPct).toBe(100);
    expect(layout.rows[0]!.offsetPct).toBe(0);
  });

  it("still shows spans caught in a parent cycle", () => {
    const layout = layoutWaterfall([
      span("a", "b", 0, 1),
      span("b", "a", 0.2, 0.8),
      span("self", "self", 0.1, 0.2),
    ]);
    expect(layout.rows.map((row) => row.span.spanId).sort()).toEqual(["a", "b", "self"]);
  });
});

describe("coveredMs", () => {
  it("merges overlapping intervals and clips to the window", () => {
    expect(coveredMs(0, 1, [[0.2, 0.5], [0.4, 0.6], [0.9, 2]])).toBeCloseTo(500);
    expect(coveredMs(0, 1, [])).toBe(0);
    expect(coveredMs(0, 1, [[2, 3]])).toBe(0);
  });
});

describe("axis ticks", () => {
  it("chooses 1, 2, or 5 times a power of ten", () => {
    expect(niceStep(1000, 5)).toBe(200);
    expect(niceStep(37, 5)).toBe(10);
    expect(niceStep(0, 5)).toBe(1);
  });

  it("positions ticks as percentages of the trace", () => {
    const ticks = timeTicks(1000, 5);
    expect(ticks.map((tick) => tick.ms)).toEqual([0, 200, 400, 600, 800, 1000]);
    expect(ticks.at(-1)!.pct).toBeCloseTo(100);
    expect(timeTicks(0)).toEqual([{ ms: 0, pct: 0 }]);
  });
});
