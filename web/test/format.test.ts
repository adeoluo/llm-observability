import { describe, expect, it } from "vitest";
import {
  formatAttribute,
  formatCost,
  formatDuration,
  formatPercent,
  formatTimestamp,
  formatTokens,
  llmDetails,
  spanError,
} from "../src/format";
import { span } from "./fixtures";

describe("formatDuration", () => {
  it.each([
    [0, "0 ms"],
    [0.85, "850 us"],
    [4.5, "4.50 ms"],
    [12.43, "12.4 ms"],
    [850, "850 ms"],
    [1250, "1.25 s"],
    [125_000, "2m 05s"],
    [-12.43, "-12.4 ms"],
    [Number.NaN, "n/a"],
  ])("formats %s ms as %s", (input, expected) => {
    expect(formatDuration(input)).toBe(expected);
  });
});

describe("number formatting", () => {
  it("formats costs with precision for small amounts", () => {
    expect(formatCost(0)).toBe("$0.00");
    expect(formatCost(0.000123)).toBe("$0.00012");
    expect(formatCost(0.5)).toBe("$0.5000");
    expect(formatCost(1234.5)).toBe("$1,234.50");
    expect(formatCost(Number.POSITIVE_INFINITY)).toBe("n/a");
  });

  it("formats token counts compactly", () => {
    expect(formatTokens(950)).toBe("950");
    expect(formatTokens(1234)).toBe("1.23k");
    expect(formatTokens(12_345)).toBe("12.3k");
    expect(formatTokens(4_200_000)).toBe("4.20M");
  });

  it("formats percentages and timestamps", () => {
    expect(formatPercent(0.0512)).toBe("5.1%");
    expect(formatPercent(0.5, 0)).toBe("50%");
    expect(formatTimestamp(0)).toBe("1970-01-01 00:00:00");
    expect(formatTimestamp(Number.NaN)).toBe("n/a");
  });

  it("formats attribute values", () => {
    expect(formatAttribute(null)).toBe("null");
    expect(formatAttribute(true)).toBe("true");
    expect(formatAttribute(42)).toBe("42");
    expect(formatAttribute(0.1 + 0.2)).toBe("0.3");
    expect(formatAttribute("gpt-6.1-sol")).toBe("gpt-6.1-sol");
  });
});

describe("span helpers", () => {
  it("extracts LLM call details", () => {
    const call = span("c", null, 0, 1, {
      attributes: {
        "llm.model": "gpt-6.1-sol",
        "llm.input_tokens": 400,
        "llm.output_tokens": 60,
        "llm.cost_usd": 0.0016,
      },
    });
    expect(llmDetails(call)).toEqual({
      model: "gpt-6.1-sol",
      inputTokens: 400,
      outputTokens: 60,
      totalTokens: 460,
      costUsd: 0.0016,
    });
    expect(llmDetails(span("plain", null, 0, 1))).toBeNull();
  });

  it("reports span errors", () => {
    expect(spanError(span("ok", null, 0, 1))).toBeNull();
    const failed = span("f", null, 0, 1, {
      status: "error",
      attributes: { "error.type": "timeout", "error.message": "provider returned timeout" },
    });
    expect(spanError(failed)).toBe("provider returned timeout");
    expect(spanError(span("bare", null, 0, 1, { status: "error" }))).toBe("error");
  });
});
