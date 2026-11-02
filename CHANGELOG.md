# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

## Unreleased

### Documentation

- Vertical layered architecture diagram
- Horizontal layered architecture diagram
- Compact horizontal architecture diagram

### Build and CI

- Run CodeQL on main and on a weekly schedule only

## [0.2.0] 2026-11-02

### Features

- **core:** Add spans, traces, and a context-managed tracer
- **metrics:** Add LLM cost modeling and metric aggregation
- **analysis:** Add exporters and multi-trace analysis
- **cli:** Add an instrumented demo and the command-line interface
- **instrumentation:** Add decorator tracing, span events, and sampling
- **formats:** Add Chrome-trace and CSV export, and trace diffing
- **alerts:** Add an alerting engine, SLO tracking, and span search
- Add HTTP service, stress benchmark, and operations documentation
- Add production observability (metrics and readiness) and reword footer
- Add TypeScript trace dashboard and trace collection API (#1)

### Documentation

- Write README, architecture diagram, and responsible-AI cards
- Add tracing benchmark and refresh the README
- Use plain, factual wording (#17)

### Maintenance

- Scaffold llm-observability from standards template
- Combine nested with in benchmark
- **deps:** Bump github/codeql-action from 3 to 4
- **deps:** Bump astral-sh/setup-uv from 4 to 7
- **deps:** Bump actions/upload-artifact from 4 to 7
- **ci:** Bump GitHub Actions to current major versions
- Remove Dependabot configuration

### Bench

- Add large-workload scale benchmark (#18)
