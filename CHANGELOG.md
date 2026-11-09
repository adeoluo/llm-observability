# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

## [0.2.1] 2026-11-09

### Bug fixes

- Current OpenAI and Claude models and prices in the default price list, with re-recorded demos and dashboard screenshots (#8)

### Documentation

- Vertical layered architecture diagram
- Horizontal layered architecture diagram
- Compact horizontal architecture diagram
- Remove authorship statements from docs and scripts
- Recorded demos of more commands, with their vhs tapes (#2)
- Recorded demos of the HTTP service and more commands (#3)
- Complete citation metadata and bump it on release (#5)
- Diagrams on white in the shared theme, make diagram for every diagram, and a self-contained Definition of Done (#7)

### Build and CI

- Run CodeQL on main and on a weekly schedule only
- Build and attach the sdist and wheel to every release (#9)
- Attach the built dashboard to every release (#10)

### Maintenance

- Add release automation, AGENTS.md, llms.txt and contributor docs
- Classify squash merges in the changelog by the commits they contain
- Latest toolchain and CI versions (#4)
- Release script keeps hard-coded version strings in step (#6)

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
