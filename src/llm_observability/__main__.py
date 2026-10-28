"""Enable ``python -m llm_observability`` to invoke the command-line interface."""

from __future__ import annotations

from llm_observability.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
