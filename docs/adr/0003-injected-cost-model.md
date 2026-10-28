# ADR-0003: An injected cost model

- **Status:** Accepted
- **Date:** 2026-01-01

## Context

Cost is a core observability metric, but provider prices change over time and vary by
model. Hard-coding prices would make the library stale and hard to test.

## Decision

Model prices as data: a `PriceList` maps model names to `ModelPrice` (per-million-token
input and output prices). Cost functions take a `PriceList`, defaulting to a built-in list
that callers can override.

## Alternatives considered

- **Hard-coded constants.** Simple but goes stale and cannot be varied in tests.
- **Fetching live prices.** Adds a network dependency and nondeterminism, against the
  offline-first design.

## Consequences

- Prices are easy to update and to override per environment.
- Cost computation is deterministic and unit-testable.
- Unknown models return a cost of zero rather than raising, so partial pricing is tolerated.
