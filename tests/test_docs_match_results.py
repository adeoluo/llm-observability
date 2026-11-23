"""The demonstration output quoted in the README and the evaluation report is current."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from llm_observability.cli import main

ROOT = Path(__file__).resolve().parent.parent


def test_quoted_demonstration_matches_the_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["demonstrate"]) == 0
    out = capsys.readouterr().out.strip()
    summary = out.splitlines()[-1]
    readme = (ROOT / "README.md").read_text()
    report = (ROOT / "docs" / "EVALUATION_REPORT.md").read_text()
    assert summary in readme
    waterfall = "\n".join(
        line for line in out.splitlines() if line.startswith(("Trace ", "- ", "  - "))
    )
    assert waterfall in readme and waterfall in report
    cost = re.search(r"\$\d+\.\d+", summary)
    tokens = re.search(r"(\d+) tokens \(in (\d+) / out (\d+)\)", summary)
    assert cost and tokens
    assert f"| Estimated cost | {cost.group()} |" in report
    assert f"| Total tokens | {tokens[1]} (in {tokens[2]} / out {tokens[3]}) |" in report
