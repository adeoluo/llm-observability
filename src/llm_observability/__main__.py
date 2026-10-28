"""Entrypoint: `python -m llm_observability`."""

from __future__ import annotations

from llm_observability import __version__
from llm_observability.configuration import settings


def main() -> None:
    header = f"Llm Observability v{__version__}"
    status = f"environment={settings.environment}, seed={settings.seed}"
    print(f"{header} - {status}")


if __name__ == "__main__":
    main()
