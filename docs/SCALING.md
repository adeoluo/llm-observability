# Scaling and Design Tradeoffs - LLM Observability

How the reference design grows, and the tradeoffs taken.

## Reference architecture (today)

A single process ingests batches of call records, builds traces with the tracing
primitives, and computes metrics and SLOs, served over a standard-library HTTP service.
Stateless per request.

## Scaling path

| Stage | Bottleneck | Change |
|---|---|---|
| One process | CPU, global interpreter lock | One replica per core |
| High ingest | Per-request overhead | Batch more records per request |
| Durable history | Statelessness | Add a store behind the ingest interface; aggregate windows |
| Many services | Cardinality of models and tags | Pre-aggregate per model/tag; roll up over time |
| Alerting at scale | Pairwise batch comparison | Stream percentiles; compare rolling windows |

Because aggregation is stateless and shared-nothing, throughput is linear in replicas.

## Substantial tradeoffs

- **Stateless aggregation vs a durable time-series store.** Computing over the request batch
  keeps the service simple, dependency-free, and horizontally trivial, at the cost of no
  history; the caller owns retention. A durable store adds history and alerting over time at
  the cost of a dependency and operational surface. Ingest sits behind an interface for that.
- **Exact percentiles vs streaming sketches.** Exact percentiles over a batch are simple and
  precise but require the batch in memory. Streaming sketches (for example t-digest) bound
  memory for unbounded streams at the cost of approximation. The reference chooses exactness
  for bounded batches.
- **Built-in price list vs a live pricing feed.** A static price list is deterministic and
  offline but goes stale; a live feed is current at the cost of a dependency. Prices are a
  single structure to update or replace.
- **Threads vs processes.** Aggregation is pure Python and GIL-bound, so processes, not
  threads, are the unit of scaling. The service is stateless to make that trivial.

## What would change under real load

Batch aggressively, run process-per-core replicas, and, for history and alerting, add a
time-series store behind the ingest interface and switch to streaming percentiles over
rolling windows. The tracing primitives, metrics, and SLO logic are unchanged.
