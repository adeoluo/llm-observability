import type { TraceFilters } from "./types";

export type Route =
  | { page: "traces"; filters: TraceFilters }
  | { page: "trace"; traceId: string }
  | { page: "summary" };

/** Parse a location hash such as "#/traces?status=error" or "#/trace/abc". */
export function parseRoute(hash: string): Route {
  const raw = hash.replace(/^#/, "");
  const [pathPart = "", queryPart = ""] = raw.split("?", 2);
  const path = pathPart.replace(/\/+$/, "") || "/traces";
  if (path.startsWith("/trace/")) {
    const traceId = decodeURIComponent(path.slice("/trace/".length));
    if (traceId) return { page: "trace", traceId };
  }
  if (path === "/summary") return { page: "summary" };
  const params = new URLSearchParams(queryPart);
  const filters: TraceFilters = {};
  const status = params.get("status");
  if (status === "ok" || status === "error") filters.status = status;
  const model = params.get("model");
  if (model) filters.model = model;
  const minLatency = params.get("min_latency_ms");
  if (minLatency !== null && minLatency !== "") {
    const value = Number(minLatency);
    if (Number.isFinite(value) && value >= 0) filters.minLatencyMs = value;
  }
  return { page: "traces", filters };
}

/** Build the hash for a route; the inverse of parseRoute. */
export function routeHash(route: Route): string {
  switch (route.page) {
    case "trace":
      return `#/trace/${encodeURIComponent(route.traceId)}`;
    case "summary":
      return "#/summary";
    case "traces": {
      const params = new URLSearchParams();
      const { status, model, minLatencyMs } = route.filters;
      if (status) params.set("status", status);
      if (model) params.set("model", model);
      if (minLatencyMs !== undefined) params.set("min_latency_ms", String(minLatencyMs));
      const query = params.toString();
      return query ? `#/traces?${query}` : "#/traces";
    }
  }
}
