# End-to-End Case Study - Measuring a Model Rollout

How the platform answers "is the new model cheaper, faster, and no less reliable?"

## Scenario

A team is rolling out a new model and needs to know, before committing, whether it changes
cost, latency, and error rate. They have a batch of recorded calls from each model.

## Summarizing a batch

```bash
curl -s -X POST localhost:8000/summarize -d '{
  "calls": [
    {"model": "gpt-4o", "input_tokens": 1000, "output_tokens": 300, "latency_ms": 820},
    {"model": "gpt-4o", "input_tokens": 1200, "output_tokens": 250, "latency_ms": 1500, "error": true}
  ],
  "slo_threshold_ms": 1000
}'
```

```json
{
  "traces": 2,
  "total_cost_usd": 0.0121,
  "total_tokens": 2750,
  "error_rate": 0.5,
  "latency_p50_ms": 1160.0,
  "latency_p95_ms": 1466.0,
  "latency_p99_ms": 1493.0,
  "slo": {"threshold_ms": 1000, "objective": 0.95, "compliance": 0.5, "met": false,
          "error_budget_remaining": -9.0}
}
```

Running the same request for each model's batch gives a like-for-like comparison of cost,
token usage, the latency distribution, error rate, and SLO compliance. The CLI
`detect_regressions` turns two such batches into explicit, thresholded regression alerts.

## What an operator sees

- **A full latency distribution, not an average.** p50, p95, and p99 show the tail, which is
  where rollouts regress.
- **Cost attributed per token.** The price list turns token counts into dollars, so a
  cheaper-per-token model shows up immediately.
- **Error budget.** The SLO report says not just whether the objective was met but how much
  budget remains, which is the signal an on-call engineer acts on.

## Takeaway

Treating each call as a timed, priced, typed span and aggregating batches into a
distribution, a cost, and an SLO turns a model rollout from a guess into a measured decision.
