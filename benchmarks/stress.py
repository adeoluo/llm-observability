"""A production-style stress benchmark for the observability service.

Drives the full summarize handler under sustained, concurrent load, ingesting
batches of synthetic LLM-call records and computing metrics and SLOs, and reports
throughput with p50, p95, and p99 handler latency. Deterministic and offline;
run with:

    uv run python benchmarks/stress.py
"""

from __future__ import annotations

import random
import statistics
import time
from concurrent.futures import ThreadPoolExecutor

from llm_observability.service import ObservabilityService, handle

_MODELS = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "claude-3-5-haiku"]


def _batch(rng: random.Random, size: int) -> dict[str, object]:
    calls = []
    for _ in range(size):
        calls.append(
            {
                "model": rng.choice(_MODELS),
                "input_tokens": rng.randint(50, 2000),
                "output_tokens": rng.randint(20, 800),
                "latency_ms": rng.uniform(80, 1500),
                "error": rng.random() < 0.05,
            }
        )
    return {"calls": calls, "slo_threshold_ms": 1000}


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(fraction * len(ordered)))]


def main() -> None:
    service = ObservabilityService()
    rng = random.Random(0)
    batch_size = 100
    requests = [_batch(rng, batch_size) for _ in range(1000)]

    def one(body: dict[str, object]) -> float:
        start = time.perf_counter()
        handle("POST", "/summarize", body, service)
        return (time.perf_counter() - start) * 1000

    print(f"Batches: {len(requests)} | Calls per batch: {batch_size}")
    for workers in (1, 4, 8):
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            latencies = list(pool.map(one, requests))
        wall = time.perf_counter() - start
        calls_per_second = len(requests) * batch_size / wall
        print(
            f"workers={workers:<2}  "
            f"{calls_per_second:>9.0f} calls/s  "
            f"p50={statistics.median(latencies):>6.2f} ms  "
            f"p95={_percentile(latencies, 0.95):>6.2f} ms  "
            f"p99={_percentile(latencies, 0.99):>6.2f} ms"
        )


if __name__ == "__main__":
    main()
