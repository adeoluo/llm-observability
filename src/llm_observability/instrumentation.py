"""Decorator-based auto-instrumentation.

Wrapping a function in a `with tracer.span(...)` block everywhere is repetitive. The
:func:`instrument` decorator traces a function automatically: each call opens a span named
for the function, records its outcome, and closes it. This is the ergonomic path to
instrumenting an existing codebase with minimal edits.

The decorator is tracer-bound (``tracer.instrument``) so it shares the tracer's context and
nesting, and it preserves the wrapped function's metadata.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, TypeVar

from llm_observability.core.tracer import Tracer

F = TypeVar("F", bound=Callable[..., Any])


def instrument(tracer: Tracer, *, name: str | None = None) -> Callable[[F], F]:
    """Return a decorator that traces each call of the wrapped function.

    Args:
        tracer: The tracer that owns the created spans.
        name: Span name; defaults to the function's qualified name.
    """

    def decorator(func: F) -> F:
        span_name = name or func.__qualname__

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.span(span_name):
                return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
