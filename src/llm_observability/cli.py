"""Command-line interface for the observability platform.

Subcommands:

- ``demonstrate`` - trace a simulated offline agent run and print the trace tree and its
  aggregated metrics (tokens, cost, latency).
- ``prices`` - list the built-in model prices.
- ``sample-traces`` - write a seeded batch of realistic sample traces as JSON, in the body
  format accepted by ``POST /api/traces``.
- ``serve`` - start the HTTP service and dashboard (``--demo-traces N`` preloads samples).

The CLI wires the demo, exporters, and metrics together; it contains no tracing logic.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from llm_observability import __version__
from llm_observability.cost import DEFAULT_PRICES
from llm_observability.demo import generate_sample_traces, simulated_agent_run
from llm_observability.exporters import render_tree, trace_to_dict
from llm_observability.metrics import aggregate_metrics


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="llm-observability",
        description="LLM observability and tracing: CLI, collector service, and dashboard host.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo_parser = subparsers.add_parser(
        "demonstrate", help="Trace a simulated agent run and show the trace and metrics."
    )
    demo_parser.set_defaults(handler=_handle_demo)

    prices_parser = subparsers.add_parser("prices", help="List built-in model prices.")
    prices_parser.set_defaults(handler=_handle_prices)

    serve_parser = subparsers.add_parser("serve", help="Start the HTTP observability service.")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host.")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    serve_parser.add_argument(
        "--demo-traces",
        type=int,
        default=0,
        metavar="N",
        help="Preload N generated sample traces so the dashboard has data.",
    )
    serve_parser.add_argument(
        "--ui-dir", type=Path, default=None, help="Built dashboard directory (web/dist)."
    )
    serve_parser.set_defaults(handler=_handle_serve)

    sample_parser = subparsers.add_parser(
        "sample-traces", help="Write generated sample traces as JSON for POST /api/traces."
    )
    sample_parser.add_argument("--count", type=int, default=200, help="Number of traces.")
    sample_parser.add_argument("--seed", type=int, default=7, help="Random seed.")
    sample_parser.add_argument(
        "--output", type=Path, default=None, help="Output file (default: stdout)."
    )
    sample_parser.set_defaults(handler=_handle_sample_traces)
    return parser


def _handle_serve(args: argparse.Namespace) -> int:  # pragma: no cover - blocks forever
    from llm_observability.service import serve

    serve(host=args.host, port=args.port, demo_traces=args.demo_traces, ui_dir=args.ui_dir)
    return 0


def _handle_sample_traces(args: argparse.Namespace) -> int:
    traces = generate_sample_traces(args.count, seed=args.seed)
    text = json.dumps({"traces": [trace_to_dict(trace) for trace in traces]})
    if args.output is None:
        print(text)
    else:
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"wrote {len(traces)} traces to {args.output}")
    return 0


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
