"""Conventions for recording LLM calls on spans, and metric aggregation.

A span becomes an "LLM call" when it carries the standard attributes this module defines:
model, input tokens, output tokens, and cost. :func:`record_llm_call` sets them
consistently; :func:`aggregate_metrics` then sums them across a trace into a
:class:`Metrics` summary (total tokens, cost, latency, call count, error count).

Centralizing the attribute keys means the aggregator and any exporter agree on where the
numbers live, without coupling to how a particular model client works.
"""

from __future__ import annotations

from dataclasses import dataclass

from llm_observability.core.span import Span, SpanStatus
from llm_observability.core.trace import Trace
from llm_observability.cost import PriceList

ATTR_MODEL = "llm.model"
ATTR_INPUT_TOKENS = "llm.input_tokens"
ATTR_OUTPUT_TOKENS = "llm.output_tokens"
ATTR_COST = "llm.cost_usd"


def record_llm_call(
    span: Span,
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    prices: PriceList | None = None,
) -> float:
    """Record standard LLM-call attributes on ``span`` and return the estimated cost."""
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    price_list = prices if prices is not None else PriceList()
    cost = price_list.estimate_cost(model, input_tokens, output_tokens)
    span.set_attribute(ATTR_MODEL, model)
    span.set_attribute(ATTR_INPUT_TOKENS, input_tokens)
    span.set_attribute(ATTR_OUTPUT_TOKENS, output_tokens)
    span.set_attribute(ATTR_COST, cost)
    return cost


@dataclass(frozen=True, slots=True)
class Metrics:
    """Aggregated metrics over a set of spans."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    llm_calls: int = 0
    total_spans: int = 0
    errors: int = 0
    latency_ms: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def format(self) -> str:
        """Render a one-line summary."""
        return (
            f"{self.llm_calls} calls, {self.total_tokens} tokens "
            f"(in {self.input_tokens} / out {self.output_tokens}), "
            f"${self.cost_usd:.4f}, {self.latency_ms:.1f} ms, {self.errors} errors"
        )


def aggregate_metrics(trace: Trace) -> Metrics:
    """Sum LLM-call metrics and latency across a trace."""
    input_tokens = 0
    output_tokens = 0
    cost = 0.0
    llm_calls = 0
    errors = 0
    for span in trace.spans:
        if span.status is SpanStatus.ERROR:
            errors += 1
        if ATTR_MODEL in span.attributes:
            llm_calls += 1
            input_tokens += int(span.attributes.get(ATTR_INPUT_TOKENS, 0))
            output_tokens += int(span.attributes.get(ATTR_OUTPUT_TOKENS, 0))
            cost += float(span.attributes.get(ATTR_COST, 0.0))
    return Metrics(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        llm_calls=llm_calls,
        total_spans=len(trace),
        errors=errors,
        latency_ms=trace.total_duration_ms,
    )
