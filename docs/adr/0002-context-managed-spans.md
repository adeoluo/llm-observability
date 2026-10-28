# ADR-0002: Context-managed spans with a context variable

- **Status:** Accepted
- **Date:** 2026-01-01

## Context

Instrumentation must capture the parent/child structure of nested operations (an agent run
containing LLM and tool calls) without forcing the caller to thread a parent span through
every function.

## Decision

Expose spans through a context manager (`with tracer.span("name"):`) and track the current
span in a `contextvars.ContextVar`. Opening a span reads the current span as its parent and
sets itself as current for the duration of the block; exiting restores the previous span
and finishes the span, setting an ERROR status if the block raised.

## Alternatives considered

- **Explicit parent arguments.** Correct but verbose and error-prone; every call site must
  pass the parent.
- **A global mutable "current span".** Breaks under concurrency; a context variable is the
  correct, async- and thread-safe mechanism.

## Consequences

- A whole call tree is instrumented with `with` blocks and nothing else.
- Error status is captured automatically.
- Timing is pluggable (a deterministic clock) for reproducible tests.
