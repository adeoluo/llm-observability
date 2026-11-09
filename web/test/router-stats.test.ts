import { describe, expect, it } from "vitest";
import { parseRoute, routeHash, type Route } from "../src/router";
import { barGeometry, histogram, niceMax, percentile } from "../src/stats";

describe("router", () => {
  it.each<[string, Route]>([
    ["", { page: "traces", filters: {} }],
    ["#/traces?status=error&model=gpt-6.1-sol&min_latency_ms=250", {
      page: "traces",
      filters: { status: "error", model: "gpt-6.1-sol", minLatencyMs: 250 },
    }],
    ["#/trace/trace%2F1", { page: "trace", traceId: "trace/1" }],
    ["#/summary", { page: "summary" }],
  ])("parses %j", (hash, route) => {
    expect(parseRoute(hash)).toEqual(route);
  });

  it("ignores invalid filter values", () => {
    expect(parseRoute("#/traces?status=bad&min_latency_ms=-3")).toEqual({
      page: "traces",
      filters: {},
    });
  });

  it("round-trips routes through the hash", () => {
    const routes: Route[] = [
      { page: "traces", filters: {} },
      { page: "traces", filters: { status: "ok", minLatencyMs: 1000 } },
      { page: "trace", traceId: "trace-0042" },
      { page: "summary" },
    ];
    for (const route of routes) expect(parseRoute(routeHash(route))).toEqual(route);
  });
});

describe("stats", () => {
  it("matches linear-interpolated percentiles", () => {
    const values = [10, 20, 30, 40, 50];
    expect(percentile(values, 50)).toBe(30);
    expect(percentile(values, 95)).toBeCloseTo(48);
    expect(percentile([], 50)).toBe(0);
    expect(() => percentile(values, 101)).toThrow(RangeError);
  });

  it("buckets values into equal-width bins", () => {
    const buckets = histogram([0, 1, 2, 3, 4, 10], 2);
    expect(buckets.map((bucket) => bucket.count)).toEqual([5, 1]);
    expect(histogram([], 4)).toEqual([]);
    expect(histogram([7, 7], 4)).toEqual([{ start: 7, end: 7, count: 2 }]);
  });

  it("rounds chart maxima up to readable values", () => {
    expect(niceMax(0)).toBe(1);
    expect(niceMax(7)).toBe(10);
    expect(niceMax(180)).toBe(200);
    expect(niceMax(0.023)).toBeCloseTo(0.025);
  });

  it("lays out bars proportionally within the chart area", () => {
    const { bars, max } = barGeometry(
      [
        { label: "a", value: 50 },
        { label: "b", value: 100 },
      ],
      200,
      100,
      0.5,
    );
    expect(max).toBe(100);
    expect(bars[1]).toMatchObject({ height: 100, y: 0, width: 50, x: 125 });
    expect(bars[0]).toMatchObject({ height: 50, y: 50, x: 25 });
  });
});
