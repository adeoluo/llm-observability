# Operations Guide - LLM Observability

The operational contract of the observability service.

## Running the service

```bash
uv run python -m llm_observability serve --host 0.0.0.0 --port 8000
```

A standard-library HTTP server with **zero runtime dependencies**. It ingests batches of
LLM-call records and returns aggregate metrics and an optional latency SLO.

## Endpoints

| Method | Path | Body | Success |
|---|---|---|---|
| GET | `/health` | none | status and known model prices |
| GET | `/ready` | none | readiness of the service |
| GET | `/metrics` | none | per-route request, error, and latency metrics (Prometheus text) |
| POST | `/summarize` | `{"calls": [...], "slo_threshold_ms"?, "slo_objective"?}` | cost, tokens, error rate, latency percentiles, SLO |

Each call record needs `model`, `input_tokens`, `output_tokens`, and `latency_ms`, with an
optional `error` flag. Errors return JSON `{"error": ...}` with a 4xx status.

## Service level objectives

Measured by `benchmarks/stress.py` (batches of 100 call records) on a developer laptop:

| Objective | Target | Observed (single worker) |
|---|---|---|
| Summarize latency p50 | < 2 ms/batch | about 0.6 ms |
| Summarize latency p99 | < 2 ms/batch at concurrency 1 | about 0.9 ms |
| Ingest throughput | > 100000 call records/second/core | about 160000 call records/second |

Illustrative targets for the reference implementation.

## Operational constraints

- **Aggregation is CPU bound and holds the global interpreter lock.** Throughput is flat
  across threads in one process and the p99 tail grows with concurrency (measured: about
  0.9 ms at one worker to tens of milliseconds at eight). Scale with **processes**, not
  threads, and batch records per request to amortize overhead.
- **Batches are bounded** to 10000 call records per request, so a single request cannot
  exhaust CPU or memory.
- **The service is stateless.** It computes over the batch in the request; it is not a
  durable store. Persist records upstream or add a store behind the ingest interface.
- **Unknown models cost zero.** Cost is estimated from a built-in price list; a model not
  in the list contributes tokens and latency but no cost. Keep the price list current.
- **No persistence, no authentication.** Front the service with a gateway.

## Failure modes and responses

| Symptom | Likely cause | Response |
|---|---|---|
| Rising p99 under load | Concurrency above one worker per core | Add replicas; batch more per request |
| Cost lower than expected | Model missing from the price list | Add the model's price |
| `400` on summarize | Missing call fields or bad SLO | Inspect the `error` field |

## Capacity planning

A single core ingests on the order of 160000 call records per second in batches. Size
replicas for peak ingest, and batch records to keep per-request overhead low.
