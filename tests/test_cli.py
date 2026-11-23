"""Tests for the demo and CLI."""

from __future__ import annotations

import pytest

from llm_observability.cli import main
from llm_observability.demo import simulated_agent_run
from llm_observability.metrics import aggregate_metrics


def test_simulated_run_produces_metrics() -> None:
    tracer = simulated_agent_run()
    trace = tracer.traces()[0]
    metrics = aggregate_metrics(trace)
    assert metrics.llm_calls == 2
    assert metrics.total_tokens == 842
    assert metrics.cost_usd > 0.0
    assert metrics.errors == 0


def test_simulated_run_is_deterministic() -> None:
    first = aggregate_metrics(simulated_agent_run().traces()[0])
    second = aggregate_metrics(simulated_agent_run().traces()[0])
    assert first == second


def test_cli_demonstrate(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["demonstrate"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "agent.run" in output
    assert "llm.call" in output
    assert "calls" in output


def test_cli_prices(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["prices"])
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "gpt-4o" in output
    assert "input" in output


def test_cli_requires_command() -> None:
    with pytest.raises(SystemExit):
        main([])
