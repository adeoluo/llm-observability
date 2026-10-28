# Data Card - LLM Observability

This project processes trace data that the instrumented application produces at runtime; it
ships no datasets. The only bundled data is an illustrative model price list.

## model prices (`src/llm_observability/cost.py`)

- **Provenance:** a small, illustrative table of public per-million-token prices for a few
  well-known models, hand-entered for demonstration.
- **Status:** not authoritative and not continuously updated; injected and overridable.
- **Licensing:** the table is authored by this repository; MIT.

## runtime trace data

- Traces are created in memory by the calling application and contain whatever attributes
  the caller records (model names, token counts, and any custom attributes).
- Operators are responsible for ensuring no sensitive content is placed in span attributes
  if traces are exported or stored.

## Ethical considerations

The library records only what the caller passes it. Treat span attributes as potentially
sensitive and redact before exporting traces outside a trusted environment.
