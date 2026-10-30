"""A large-workload scale benchmark for trace aggregation and search.

Where ``benchmark.py`` quotes raw span-creation and aggregation throughput and
``stress.py`` drives the HTTP service under concurrent load, this script measures
the core analysis operations - :func:`summarize_batch` (aggregate a batch of
traces into metrics and latency percentiles) and :func:`search_spans` (the query
layer) - on progressively larger volumes of synthetic traces. It reports
wall-clock aggregation time, throughput, peak memory (via the standard-library
:mod:`tracemalloc`), the number of spans ingested, and the query latency for a
span search across the whole batch.

The traces are produced by the real tracer over deterministically generated
LLM-call records (nothing is downloaded), so the run is reproducible and fully
offline. Run with:

    uv run python benchmarks/scale.py
"""

from __future__ import annotations

import time
import tracemalloc
from dataclasses import dataclass

from llm_observability.analysis import summarize_batch
from llm_observability.core import Tracer
from llm_observability.core.trace import Trace
from llm_observability.metrics import record_llm_call
from llm_observability.search import search_spans

WORKLOAD_SIZES: tuple[int, ...] = (5_000, 15_000, 30_000, 60_000)

_MODELS: tuple[str, ...] = ("gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-5-haiku")


def _generate_traces(count: int) -> list[Trace]:
    """Produce ``count`` synthetic traces, each an agent run with one LLM call."""
    traces: list[Trace] = []
    for index in range(count):
        tracer = Tracer()
        with tracer.span("agent.run"), tracer.span("llm.call") as span:
            record_llm_call(
                span,
                model=_MODELS[index % len(_MODELS)],
                input_tokens=50 + index % 2_000,
                output_tokens=20 + index % 800,
            )
        traces.extend(tracer.traces())
    return traces


@dataclass(frozen=True, slots=True)
class ScaleRow:
    """One measured row of the scale sweep."""

    size: int
    seconds: float
    throughput: float
    peak_mib: float
    spans: int
    query_ms: float


def run_workload(size: int) -> ScaleRow:
    """Aggregate and query ``size`` synthetic traces.

    Timing and throughput cover :func:`summarize_batch`; memory is the peak
    additional allocation of the aggregation and query (the per-trace metrics
    and the matched-span list), and the quality columns are the total span count
    and the latency of a span search across the batch.
    """
    traces = _generate_traces(size)
    tracemalloc.start()
    start = time.perf_counter()
    summary = summarize_batch(traces)
    elapsed = time.perf_counter() - start
    query_start = time.perf_counter()
    hits = search_spans(traces, name_contains="llm.call")
    query_ms = (time.perf_counter() - query_start) * 1000
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    spans = sum(len(trace.spans) for trace in traces)
    throughput = summary.num_traces / elapsed if elapsed > 0 else float("inf")
    assert len(hits) == size
    return ScaleRow(size, elapsed, throughput, peak / (1024 * 1024), spans, query_ms)


def main() -> None:
    print("LLM Observability scale benchmark")
    print("Data is SYNTHETIC: traces produced by the tracer over generated LLM-call records.")
    print()
    header = (
        f"{'traces':>8}  {'agg (s)':>8}  {'traces/sec':>11}  "
        f"{'peak MiB':>9}  {'spans':>9}  {'query (ms)':>11}"
    )
    print(header)
    print("-" * len(header))
    for size in WORKLOAD_SIZES:
        row = run_workload(size)
        print(
            f"{row.size:>8,}  {row.seconds:>8.3f}  {row.throughput:>11,.0f}  "
            f"{row.peak_mib:>9.2f}  {row.spans:>9,}  {row.query_ms:>11.2f}"
        )


if __name__ == "__main__":
    main()
