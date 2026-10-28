"""LLM cost modeling.

Cost is one of the three numbers observability must surface (alongside latency and
tokens). A :class:`PriceList` maps a model name to its per-token input and output prices;
:func:`estimate_cost` turns a token count into dollars. Prices are expressed per million
tokens, the industry convention, and are injected rather than hard-coded so they stay
current and testable.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelPrice:
    """Per-million-token input and output prices for one model, in US dollars."""

    input_per_million: float
    output_per_million: float

    def cost(self, input_tokens: int, output_tokens: int) -> float:
        """Return the dollar cost of the given token counts."""
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be non-negative")
        return (
            input_tokens * self.input_per_million + output_tokens * self.output_per_million
        ) / 1_000_000


# Illustrative public prices (US dollars per million tokens). Injected, not authoritative;
# update as provider pricing changes.
DEFAULT_PRICES: dict[str, ModelPrice] = {
    "gpt-4o": ModelPrice(2.50, 10.00),
    "gpt-4o-mini": ModelPrice(0.15, 0.60),
    "claude-3-5-sonnet": ModelPrice(3.00, 15.00),
    "claude-3-5-haiku": ModelPrice(0.80, 4.00),
}


class PriceList:
    """A lookup of model prices with graceful handling of unknown models."""

    def __init__(self, prices: dict[str, ModelPrice] | None = None) -> None:
        self._prices = dict(prices) if prices is not None else dict(DEFAULT_PRICES)

    def __contains__(self, model: str) -> bool:
        return model in self._prices

    def price_for(self, model: str) -> ModelPrice | None:
        """Return the price for ``model``, or ``None`` if unknown."""
        return self._prices.get(model)

    def estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a call; returns 0.0 for an unknown model."""
        price = self._prices.get(model)
        if price is None:
            return 0.0
        return price.cost(input_tokens, output_tokens)
