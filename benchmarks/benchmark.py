"""A micro-benchmark for tracing overhead.

Measures how many spans per second the tracer can create and finish, and how fast a batch
of traces aggregates into metrics, so the README can quote the instrumentation overhead.
Run with:

    uv run python benchmarks/benchmark.py
"""

from __future__ import annotations

import time

from llm_observability.analysis import summarize_batch
from llm_observability.core import Tracer
from llm_observability.metrics import record_llm_call


def _bench_span_creation(num_spans: int) -> float:
    tracer = Tracer()
    start = time.perf_counter()
    for _ in range(num_spans):
        with tracer.span("op") as span:
            span.set_attribute("k", "v")
    elapsed = time.perf_counter() - start
    return num_spans / elapsed if elapsed > 0 else float("inf")


def _bench_aggregation(num_traces: int) -> float:
    traces = []
    for _ in range(num_traces):
        tracer = Tracer()
        with tracer.span("agent.run"):
            with tracer.span("llm.call") as span:
                record_llm_call(span, model="gpt-4o", input_tokens=500, output_tokens=200)
        traces.extend(tracer.traces())
    start = time.perf_counter()
    summarize_batch(traces)
    elapsed = time.perf_counter() - start
    return num_traces / elapsed if elapsed > 0 else float("inf")


def main() -> None:
    spans_per_sec = _bench_span_creation(50_000)
    traces_per_sec = _bench_aggregation(10_000)
    print("LLM Observability micro-benchmark\n")
    print(f"  span create + finish : {spans_per_sec:>12,.0f} spans/sec")
    print(f"  batch aggregation    : {traces_per_sec:>12,.0f} traces/sec")


if __name__ == "__main__":
    main()
