# System Card - LLM Observability

## Overview

- **What it is:** a tracing and metrics library for LLM applications - spans, trace trees,
  cost and token metrics, and regression analysis.
- **What it is not:** a model, a tokenizer, or a billing system. Token counts and prices
  are provided by the caller.
- **Version:** 0.1.0.

## Intended use

- **Primary use cases:** instrumenting agent and retrieval pipelines; measuring latency,
  tokens, and cost; catching performance or cost regressions between deployments.
- **Primary users:** engineers operating LLM applications.

## Out-of-scope / prohibited use

- Not a distributed tracing backend; it traces within a single process.
- Cost figures are estimates, not authoritative billing.

## Performance

The deterministic demo traces a multi-step run and aggregates metrics in well under a
millisecond. Correctness of nesting, aggregation, and regression detection is covered by
tests.

## Risks and limitations

- In-memory and single-process; no cross-service propagation.
- Estimated cost depends on an injected price list that the operator must keep current.

## Safety mitigations

- Deterministic, offline, reproducible; no network calls.
- Lossless JSON export supports external auditing of traces.

## Environmental / cost footprint

Negligible; the library performs only in-memory bookkeeping.
