"""Unit tests for the LLM estimation service."""

from collections.abc import Iterator

import pytest

from app.config import Settings
from app.services import llm_service
from app.services.llm_service import (
    GenerationOptions,
    LlmConfigurationError,
    build_system_prompt,
    generate_estimation,
)


def _fake_response(*, estimation: str = "## Estimation\nTotal hours: 10", finish_reason: str = "stop") -> dict:
    return {
        "estimation": estimation,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "finish_reason": finish_reason,
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "latency_ms": 12,
        "estimated_cost_usd": 0.000045,
        "cache_hit": False,
    }


@pytest.fixture
def call_log(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict]]:
    calls: list[dict] = []

    def fake(
        *,
        system_prompt: str,
        user_message: str,
        model_override: str | None,
        max_tokens: int,
        thinking_budget: int | None,
    ) -> dict:
        calls.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "model_override": model_override,
                "max_tokens": max_tokens,
                "thinking_budget": thinking_budget,
            }
        )
        finish_reason = "length" if max_tokens <= 200 else "stop"
        return _fake_response(finish_reason=finish_reason)

    monkeypatch.setattr(llm_service, "_invoke_llm", fake)
    yield calls


class TestBuildSystemPrompt:
    def test_includes_role_rates_and_examples(self) -> None:
        prompt = build_system_prompt()

        assert "senior software consultant" in prompt.lower()
        assert "62.50 EUR/hour" in prompt
        assert "--- EXAMPLE 1 ---" in prompt
        assert "--- EXAMPLE 2 ---" in prompt
        assert "| Task | Hours | Cost (EUR) |" in prompt

    def test_json_format_renders_reference_block(self) -> None:
        prompt = build_system_prompt(example_format="json", num_examples=2)
        assert "Reference examples (JSON):" in prompt

    def test_use_examples_false_omits_examples(self) -> None:
        prompt = build_system_prompt(use_examples=False)
        assert "EXAMPLE 1" not in prompt
        assert "Reference examples" not in prompt

    def test_inline_cleaning_adds_instruction_block(self) -> None:
        prompt = build_system_prompt(inline_cleaning=True)
        assert "Informal small talk" in prompt


class TestGenerateEstimation:
    def test_rejects_empty_transcription(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            generate_estimation("")
        with pytest.raises(ValueError, match="empty"):
            generate_estimation("   ")

    def test_default_call_returns_cache_and_cost_fields(self, call_log: list[dict]) -> None:
        result = generate_estimation("Client needs a CRM with contacts and deals.")

        assert result["estimation"].startswith("## Estimation")
        assert result["provider"] == "openai"
        assert result["model"] == "gpt-4o-mini"
        assert result["estimated_cost_usd"] == 0.000045
        assert result["cache_hit"] is False
        assert result["preprocessing"] == "none"
        assert result["extracted_requirements"] is None
        assert result["usage"]["preprocessing_input_tokens"] == 0
        assert len(call_log) == 1
        assert "Client needs a CRM with contacts and deals." in call_log[0]["user_message"]

    def test_two_phase_invokes_llm_twice(self, call_log: list[dict]) -> None:
        result = generate_estimation(
            "Client needs a CRM.",
            GenerationOptions(preprocessing="two_phase"),
        )

        assert len(call_log) == 2
        assert result["preprocessing"] == "two_phase"
        assert result["extracted_requirements"] == result["estimation"]
        assert call_log[1]["user_message"] == result["extracted_requirements"]
        assert result["estimated_cost_usd"] == pytest.approx(0.00009)
        assert result["usage"]["preprocessing_input_tokens"] == 100

    def test_model_override_is_forwarded(self, call_log: list[dict]) -> None:
        generate_estimation("Some transcription", GenerationOptions(model="gpt-4o"))
        assert call_log[0]["model_override"] == "gpt-4o"

    def test_missing_api_keys_raise(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            llm_service,
            "get_settings",
            lambda: Settings(openai_api_key="", anthropic_api_key="", _env_file=None),
        )
        with pytest.raises(LlmConfigurationError, match="OPENAI_API_KEY"):
            generate_estimation("Some transcription")
