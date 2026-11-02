# AGENTS.md

Working notes for coding agents and contributors in **LLM Observability**. The [README](README.md)
explains what the project does and why; this file explains how to change it safely.

## Project

LLM tracing with a Python library and collector service, a JSON API, and a TypeScript dashboard for traces, latency, tokens, and cost.

## Layout

- `benchmarks/`: benchmark scripts and recorded results
- `docker-compose.yml`: local container setup
- `docs/`: documentation, architecture diagram source and render, design records
- `src/`: library and service source
- `tests/`: test suite
- `web/`: TypeScript dashboard

Key modules:

- `src/llm_observability/__init__.py`: LLM Observability: tracing, metrics, a collector service, and a JSON API for a web dashboard.
- `src/llm_observability/alerts.py`: An alerting rules engine over trace metrics.
- `src/llm_observability/analysis.py`: Analysis over many traces: summaries, percentiles, and regression detection.
- `src/llm_observability/cli.py`: Command-line interface for the observability platform.
- `src/llm_observability/core/__init__.py`: Core tracing abstractions.
- `src/llm_observability/core/span.py`: Core span types for tracing.
- `src/llm_observability/core/trace.py`: The :class:`Trace`: the tree of spans from one top-level operation.
- `src/llm_observability/core/tracer.py`: The :class:`Tracer`: creates spans and maintains the parent/child context.
- `src/llm_observability/cost.py`: LLM cost modeling.
- `src/llm_observability/demo.py`: A worked example: instrumenting a simulated agent run.
- `src/llm_observability/diff.py`: Diffing two traces of the same operation.
- `src/llm_observability/exporters.py`: Exporters: render and serialize traces.
- `src/llm_observability/formats.py`: Additional export formats: Chrome trace, CSV, and span-flattening.
- `src/llm_observability/instrumentation.py`: Decorator-based auto-instrumentation.
- `src/llm_observability/metrics.py`: Conventions for recording LLM calls on spans, and metric aggregation.
- `src/llm_observability/observability.py`: In-process request metrics for the HTTP service.
- `src/llm_observability/sampling.py`: Trace sampling.
- `src/llm_observability/search.py`: Searching and filtering spans across traces.
- `src/llm_observability/service.py`: The HTTP service (collector and JSON API) built on the standard library.
- `src/llm_observability/slo.py`: Service-level objective (SLO) tracking.
- `src/llm_observability/store.py`: An in-memory trace store and the JSON views the dashboard reads.
- `web/src/api.ts`
- `web/src/components/App.tsx`
- `web/src/components/SpanPanel.tsx`
- `web/src/components/SummaryPage.tsx`
- `web/src/components/TraceDetailPage.tsx`
- `web/src/components/TraceListPage.tsx`
- `web/src/components/Waterfall.tsx`
- `web/src/components/charts.tsx`
- `web/src/components/useAsync.ts`
- `web/src/format.ts`
- `web/src/main.tsx`
- `web/src/router.ts`
- `web/src/stats.ts`
- `web/src/types.ts`
- `web/src/waterfall.ts`

## Commands

| Command | Purpose |
|---|---|
| `make help` | Show this help |
| `make setup` | Install dependencies and pre-commit hooks |
| `make format` | Format automatically |
| `make lint` | Lint (no fixes) |
| `make type` | Type-check |
| `make test` | Run tests |
| `make coverage` | Tests with coverage gate |
| `make evaluation` | Reproduce the results table |
| `make run` | Run the application entrypoint |
| `make diagram` | Render architecture diagram to SVG |
| `make docker-build` | Build the image |
| `make docker-up` | Run via docker compose |
| `make clean` | Remove caches and artifacts |
| `make all` | Full local gate (mirror of continuous integration) |
| `make changelog` | Regenerate CHANGELOG.md from Conventional Commits (git-cliff) |
| `make cut-release` | Cut a release locally: version bump, changelog, tag, GitHub release (RELEASE_VERSION=vX.Y.Z optional) |

Run the full local gate (`make all`) before committing; CI runs the same checks.

## Conventions

- Commits follow Conventional Commits (`feat:`, `fix:`, `perf:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`).
  The changelog and the next version number are derived from them.
- Every number quoted in the README is produced by a command in this repository. When behavior
  changes, rerun that command and update the number in the same commit.
- When a component is added, removed or renamed, update `docs/architecture/architecture.mmd`
  and re-render `architecture.svg` so the diagram matches the code.
- README sections keep their fixed order. Prose avoids em and en dashes and promotional wording.
- Tests accompany behavior changes; a bug fix comes with a test that fails without it.
- Releases are cut with `make cut-release`.

## Python notes

- Python is managed with `uv`; run commands through `uv run` so the locked environment is used.
- Lint and format with `ruff`; type-check with `mypy`; tests use `pytest`.
- Public functions carry type hints and a docstring that states the contract, not the steps.

## TypeScript notes

- Node and npm; `npm ci` installs the locked dependencies.
- ESLint and the TypeScript compiler run in strict mode; tests use Vitest.
- Inputs crossing a process boundary are validated with a schema before use.
