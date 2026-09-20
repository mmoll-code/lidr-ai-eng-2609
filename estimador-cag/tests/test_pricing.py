"""Unit tests for LLM cost estimation."""

from app.services.pricing import estimate_cost_usd


class TestEstimateCostUsd:
    def test_gpt_4o_mini_computes_expected_cost(self) -> None:
        # gpt-4o-mini: $0.15 / 1M input, $0.60 / 1M output
        # 1_000_000 input + 1_000_000 output => 0.15 + 0.60 = 0.75
        cost = estimate_cost_usd("gpt-4o-mini", 1_000_000, 1_000_000)
        assert cost == 0.75

    def test_gpt_4o_mini_small_usage_rounds_to_six_decimals(self) -> None:
        # 100 input => 0.000015, 50 output => 0.00003 => 0.000045
        cost = estimate_cost_usd("gpt-4o-mini", 100, 50)
        assert cost == 0.000045

    def test_claude_3_5_sonnet_computes_expected_cost(self) -> None:
        # claude-3-5-sonnet-20240620: $3.00 / 1M input, $15.00 / 1M output
        cost = estimate_cost_usd("claude-3-5-sonnet-20240620", 1_000_000, 1_000_000)
        assert cost == 18.0

    def test_unknown_model_returns_none(self) -> None:
        assert estimate_cost_usd("unknown-model", 100, 50) is None

    def test_missing_input_tokens_returns_none(self) -> None:
        assert estimate_cost_usd("gpt-4o-mini", None, 50) is None

    def test_missing_output_tokens_returns_none(self) -> None:
        assert estimate_cost_usd("gpt-4o-mini", 100, None) is None
