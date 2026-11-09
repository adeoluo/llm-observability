"""A worked example: instrumenting a simulated agent run.

This module shows how the library is used end to end. :func:`simulated_agent_run` traces a
deterministic, offline "agent" that makes a couple of LLM calls and a tool call under a
root span, recording token usage and cost on the LLM spans. It returns the tracer so the
caller can render the trace and aggregate metrics - which is exactly what the CLI does.

Because timing uses the tracer's deterministic clock, the demonstration's numbers are
reproducible. :func:`generate_sample_traces` builds a larger, seeded batch of varied traces
(chat, retrieval, and agent runs) that the HTTP service can preload for the dashboard.
"""

from __future__ import annotations

import itertools
import random

from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace
from llm_observability.core.tracer import Tracer
from llm_observability.metrics import record_llm_call


def simulated_agent_run() -> Tracer:
    """Trace a deterministic, offline multi-step agent run and return the tracer."""
    tracer = Tracer(clock=itertools.count(step=5))
    with tracer.span("agent.run", question="What is 21 * 2 and the capital of France?"):
        with tracer.span("llm.call", step=1) as plan:
            record_llm_call(plan, model="gpt-6.1-sol", input_tokens=320, output_tokens=48)
        with tracer.span("tool.exec", tool="calculator", input="21 * 2") as tool:
            tool.set_attribute("output", "42")
        with tracer.span("llm.call", step=2) as answer:
            record_llm_call(answer, model="gpt-6.1-sol", input_tokens=410, output_tokens=64)
    return tracer


# Sample-trace generation for the dashboard ------------------------------------------------

_SAMPLE_EPOCH = 1_793_000_000.0
_MS_PER_OUTPUT_TOKEN = {
    "gpt-6.1-sol": 11.0,
    "gpt-6-luna": 6.0,
    "claude-sonnet-5-5": 13.0,
    "claude-haiku-5-5": 7.0,
}
_TOOLS = ("web_search", "calculator", "sql_query", "weather_lookup")
_ERROR_TYPES = ("rate_limit", "timeout", "invalid_request")


class _TraceBuilder:
    """Builds one trace with explicit timestamps (seconds) for sample data."""

    def __init__(self, trace_id: str, rng: random.Random) -> None:
        self.trace_id = trace_id
        self.rng = rng
        self.spans: list[Span] = []
        self._ids = itertools.count(1)

    def span(self, name: str, parent: Span | None, start: float, duration_ms: float) -> Span:
        span = Span(
            name=name,
            span_id=f"{self.trace_id}-s{next(self._ids)}",
            trace_id=self.trace_id,
            parent_id=parent.span_id if parent is not None else None,
            start_time=start,
            end_time=start + duration_ms / 1000.0,
            status=SpanStatus.OK,
        )
        self.spans.append(span)
        return span

    def llm_call(
        self, parent: Span, start: float, model: str, *, error_rate: float, step: str
    ) -> Span:
        rng = self.rng
        input_tokens = int(rng.lognormvariate(6.2, 0.6))
        output_tokens = int(rng.lognormvariate(4.6, 0.7))
        failed = rng.random() < error_rate
        if failed:
            output_tokens = 0
        latency = rng.uniform(180.0, 650.0) + output_tokens * _MS_PER_OUTPUT_TOKEN[model]
        if failed:
            latency = rng.uniform(800.0, 3000.0)
        span = self.span("llm.call", parent, start, latency)
        span.set_attribute("llm.step", step)
        record_llm_call(span, model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        if failed:
            error_type = rng.choice(_ERROR_TYPES)
            span.status = SpanStatus.ERROR
            span.set_attribute("error.type", error_type)
            span.set_attribute("error.message", f"provider returned {error_type}")
            span.add_event("exception", timestamp=span.end_time, type=error_type)
        return span


def _end(span: Span) -> float:
    return span.end_time if span.end_time is not None else span.start_time


def _chat_trace(builder: _TraceBuilder, start: float, model: str) -> list[Span]:
    root = builder.span("chat.request", None, start, 0.0)
    call = builder.llm_call(root, start + 0.004, model, error_rate=0.04, step="answer")
    root.end_time = _end(call) + 0.003
    root.status = call.status
    return builder.spans


def _rag_trace(builder: _TraceBuilder, start: float, model: str) -> list[Span]:
    rng = builder.rng
    root = builder.span("rag.query", None, start, 0.0)
    root.set_attribute("retrieval.top_k", 5)
    embed = builder.span("retrieval.embed", root, start + 0.002, rng.uniform(20.0, 70.0))
    search = builder.span("vector.search", root, _end(embed) + 0.001, rng.uniform(15.0, 120.0))
    search.set_attribute("retrieval.documents", 5)
    rerank = builder.span("retrieval.rerank", root, _end(search) + 0.001, rng.uniform(30.0, 90.0))
    call = builder.llm_call(root, _end(rerank) + 0.002, model, error_rate=0.05, step="generate")
    root.end_time = _end(call) + 0.004
    root.status = call.status
    return builder.spans


def _agent_trace(builder: _TraceBuilder, start: float, model: str) -> list[Span]:
    rng = builder.rng
    root = builder.span("agent.run", None, start, 0.0)
    cursor = start + 0.003
    plan = builder.llm_call(root, cursor, model, error_rate=0.06, step="plan")
    cursor = _end(plan) + 0.002
    if plan.status is SpanStatus.ERROR:
        plan = builder.llm_call(root, cursor, model, error_rate=0.0, step="plan.retry")
        cursor = _end(plan) + 0.002
    for _ in range(rng.randint(1, 3)):
        tool_name = rng.choice(_TOOLS)
        tool = builder.span("tool.exec", root, cursor, 0.0)
        tool.set_attribute("tool.name", tool_name)
        inner = builder.span("http.request", tool, cursor + 0.002, rng.lognormvariate(4.8, 0.6))
        inner.set_attribute("http.status_code", 200)
        tool.end_time = _end(inner) + 0.003
        cursor = tool.end_time + 0.002
    answer = builder.llm_call(root, cursor, model, error_rate=0.04, step="answer")
    root.end_time = _end(answer) + 0.003
    root.status = answer.status
    return builder.spans


def generate_sample_traces(count: int = 200, *, seed: int = 7) -> list[Trace]:
    """Generate ``count`` realistic, reproducible sample traces for the dashboard.

    The mix covers single chat completions, retrieval-augmented queries, and multi-step
    agent runs with nested tool calls, across several models, with occasional provider
    errors and retries.
    """
    if count < 0:
        raise ValueError("count must be non-negative")
    rng = random.Random(seed)
    shapes = (_chat_trace, _rag_trace, _agent_trace)
    models = tuple(_MS_PER_OUTPUT_TOKEN)
    traces: list[Trace] = []
    start = _SAMPLE_EPOCH
    for index in range(count):
        start += rng.expovariate(1 / 20.0)
        builder = _TraceBuilder(f"trace-{index + 1:04d}", rng)
        shape = rng.choices(shapes, weights=(4, 3, 3))[0]
        model = rng.choices(models, weights=(3, 4, 2, 2))[0]
        spans = shape(builder, start, model)
        traces.append(Trace(builder.trace_id, spans))
    return traces
