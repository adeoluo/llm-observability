"""A worked example: instrumenting a simulated agent run.

This module shows how the library is used end to end. :func:`simulated_agent_run` traces a
deterministic, offline "agent" that makes a couple of LLM calls and a tool call under a
root span, recording token usage and cost on the LLM spans. It returns the tracer so the
caller can render the trace and aggregate metrics - which is exactly what the CLI does.

Because timing uses the tracer's deterministic clock, the demonstration's numbers are
reproducible.
"""

from __future__ import annotations

import itertools

from llm_observability.core.tracer import Tracer
from llm_observability.metrics import record_llm_call


def simulated_agent_run() -> Tracer:
    """Trace a deterministic, offline multi-step agent run and return the tracer."""
    tracer = Tracer(clock=itertools.count(step=5))
    with tracer.span("agent.run", question="What is 21 * 2 and the capital of France?"):
        with tracer.span("llm.call", step=1) as plan:
            record_llm_call(plan, model="gpt-4o", input_tokens=320, output_tokens=48)
        with tracer.span("tool.exec", tool="calculator", input="21 * 2") as tool:
            tool.set_attribute("output", "42")
        with tracer.span("llm.call", step=2) as answer:
            record_llm_call(answer, model="gpt-4o", input_tokens=410, output_tokens=64)
    return tracer
