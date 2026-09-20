"""Approximate USD pricing for supported LLM models (per 1M tokens)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


# Prices as of implementation; approximate and may drift from provider rates.
MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-4o-mini": ModelPricing(input_per_million=0.15, output_per_million=0.60),
    "gpt-4o": ModelPricing(input_per_million=2.50, output_per_million=10.00),
    "claude-3-5-sonnet-20240620": ModelPricing(
        input_per_million=3.00, output_per_million=15.00
    ),
    "claude-haiku-4-5-20251001": ModelPricing(
        input_per_million=1.00, output_per_million=5.00
    ),
}


def estimate_cost_usd(
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    """Estimate request cost in USD. Returns None when model or usage is unknown."""
    if input_tokens is None or output_tokens is None:
        return None

    pricing = MODEL_PRICING.get(model)
    if pricing is None:
        return None

    cost = (
        input_tokens * pricing.input_per_million
        + output_tokens * pricing.output_per_million
    ) / 1_000_000
    return round(cost, 6)
