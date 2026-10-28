# Evaluation Report - LLM Observability

> Reproduce with `python -m llm_observability demonstrate`. Timing uses the tracer's
> deterministic clock, so the numbers are exact and stable.

## Setup

- A simulated multi-step agent run: a root `agent.run` span containing two `llm.call`
  spans and one `tool.exec` span, with token usage recorded on the LLM spans and cost
  computed from the built-in price list.

## Results

| Metric | Value |
|---|---|
| LLM calls | 2 |
| Total tokens | 842 (in 730 / out 112) |
| Estimated cost | $0.0029 |
| Spans | 4 |
| Errors | 0 |

Rendered waterfall:

```text
Trace trace-1 (35000.0 ms)
- agent.run [ok] 35000.0 ms
  - llm.call [ok] 5000.0 ms
  - tool.exec [ok] 5000.0 ms
  - llm.call [ok] 5000.0 ms
```

## Analysis capabilities

The analysis module aggregates many traces into p50/p95/p99 latency and totals, and
`detect_regressions` flags latency, cost-per-trace, and error-rate increases beyond
configurable tolerances. These are covered by tests that construct controlled baseline and
candidate batches.

## Reproducibility

Everything is offline and deterministic; the numbers above regenerate exactly.
