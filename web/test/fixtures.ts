import type { SpanRecord } from "../src/types";

export function span(
  spanId: string,
  parentId: string | null,
  startTime: number,
  endTime: number | null,
  extra: Partial<SpanRecord> = {},
): SpanRecord {
  return {
    spanId,
    traceId: "t1",
    parentId,
    name: spanId,
    startTime,
    endTime,
    status: "ok",
    attributes: {},
    events: [],
    ...extra,
  };
}
