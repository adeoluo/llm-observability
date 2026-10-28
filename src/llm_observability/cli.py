"""Command-line interface for the observability platform.

Subcommands:

- ``demonstrate`` - trace a simulated offline agent run and print the trace tree and its
  aggregated metrics (tokens, cost, latency).
- ``prices`` - list the built-in model prices.

The CLI wires the demo, exporters, and metrics together; it contains no tracing logic.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from llm_observability import __version__
from llm_observability.cost import DEFAULT_PRICES
from llm_observability.demo import simulated_agent_run
from llm_observability.exporters import render_tree
from llm_observability.metrics import aggregate_metrics


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="llm-observability",
        description="An LLM observability and tracing platform built from scratch.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser(
        "demonstrate", help="Trace a simulated agent run and show the trace and metrics."
    )
    demo_parser.set_defaults(handler=_handle_demo)

    prices_parser = subparsers.add_parser("prices", help="List built-in model prices.")
    prices_parser.set_defaults(handler=_handle_prices)
    return parser


def _handle_demo(_: argparse.Namespace) -> int:
    tracer = simulated_agent_run()
    trace = tracer.traces()[0]
    print(render_tree(trace))
    print()
    print(aggregate_metrics(trace).format())
    return 0


def _handle_prices(_: argparse.Namespace) -> int:
    print("Model prices (US dollars per million tokens):")
    for model, price in sorted(DEFAULT_PRICES.items()):
        line = (
            f"  {model:<20} input ${price.input_per_million:.2f}  "
            f"output ${price.output_per_million:.2f}"
        )
        print(line)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    exit_code: int = handler(args)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
