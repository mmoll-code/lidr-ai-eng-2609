"""HTTP tests for the estimation endpoint."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.context.examples import CANONICAL_EXAMPLES
from app.services import llm_service
from app.services.llm_service import LlmConfigurationError, LLMServiceError

ESTIMATE_URL = "/api/v1/estimate"
TRANSCRIPTION = "We need a small CRM with auth, contacts and roles. MVP six weeks."
WELL_FORMED_MD = CANONICAL_EXAMPLES[0].estimation_markdown


def _fake_response(*, estimation: str = WELL_FORMED_MD, finish_reason: str = "stop") -> dict:
    return {
        "estimation": estimation,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "finish_reason": finish_reason,
        "usage": {"input_tokens": 1234, "output_tokens": 567, "total_tokens": 1801},
        "latency_ms": 12,
        "estimated_cost_usd": 0.001234,
        "cache_hit": False,
    }


@pytest.fixture
def call_log(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
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
    return calls


class TestCreateEstimation:
    def test_returns_estimation_with_usage_cost_and_validation(
        self, client: TestClient, call_log: list[dict]
    ) -> None:
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION})

        assert response.status_code == 200
        body = response.json()
        assert body["estimation"] == WELL_FORMED_MD
        assert body["model"] == "gpt-4o-mini"
        assert body["provider"] == "openai"
        assert body["usage"]["input_tokens"] == 1234
        assert body["usage"]["output_tokens"] == 567
        assert body["usage"]["total_tokens"] == 1801
        assert body["estimated_cost_usd"] == 0.001234
        assert body["preprocessing"] == "none"
        assert body["finish_reason"] == "stop"
        assert body["cache_hit"] is False
        assert body["extracted_requirements"] is None
        assert body["validation"]["score"] == 1.0
        datetime.fromisoformat(body["generated_at"])
        assert len(call_log) == 1

    def test_missing_transcription_returns_422(self, client: TestClient) -> None:
        response = client.post(ESTIMATE_URL, json={})
        assert response.status_code == 422

    def test_empty_transcription_returns_422(self, client: TestClient) -> None:
        response = client.post(ESTIMATE_URL, json={"transcription": ""})
        assert response.status_code == 422

    def test_whitespace_transcription_returns_422(self, client: TestClient) -> None:
        response = client.post(ESTIMATE_URL, json={"transcription": "   "})
        assert response.status_code == 422

    def test_llm_configuration_error_returns_503(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> dict:
            raise LlmConfigurationError("OpenAI API key is not configured")

        monkeypatch.setattr(llm_service, "_invoke_llm", boom)
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION})
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    def test_provider_failure_returns_502(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> dict:
            raise RuntimeError("connection reset")

        monkeypatch.setattr(llm_service, "_invoke_llm", boom)
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION})
        assert response.status_code == 502
        assert "failed" in response.json()["detail"].lower()

    def test_llm_service_error_returns_502(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def boom(*args: object, **kwargs: object) -> dict:
            raise LLMServiceError("LLM call failed: connection reset")

        monkeypatch.setattr(llm_service, "generate_estimation", boom)
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION})
        assert response.status_code == 502

    def test_two_phase_invokes_llm_twice_and_fills_extracted(
        self, client: TestClient, call_log: list[dict]
    ) -> None:
        response = client.post(
            ESTIMATE_URL,
            json={"transcription": TRANSCRIPTION, "preprocessing": "two_phase"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["preprocessing"] == "two_phase"
        assert body["extracted_requirements"] is not None
        assert len(call_log) == 2
        assert call_log[1]["user_message"] == body["extracted_requirements"]

    def test_max_tokens_low_propagates_finish_reason_length(
        self, client: TestClient, call_log: list[dict]
    ) -> None:
        response = client.post(
            ESTIMATE_URL,
            json={"transcription": TRANSCRIPTION, "max_tokens": 200},
        )
        body = response.json()
        assert response.status_code == 200
        assert body["finish_reason"] == "length"
        assert body["validation"]["finish_reason_ok"] is False

    def test_example_format_json_returns_200(self, client: TestClient, call_log: list[dict]) -> None:
        response = client.post(
            ESTIMATE_URL,
            json={"transcription": TRANSCRIPTION, "example_format": "json", "num_examples": 2},
        )
        assert response.status_code == 200
        assert "Reference examples (JSON):" in call_log[0]["system_prompt"]

    def test_model_override_is_passed_to_provider(
        self, client: TestClient, call_log: list[dict]
    ) -> None:
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION, "model": "gpt-4o"})
        assert response.status_code == 200
        assert call_log[0]["model_override"] == "gpt-4o"

    def test_use_examples_false_omits_examples_block(
        self, client: TestClient, call_log: list[dict]
    ) -> None:
        response = client.post(
            ESTIMATE_URL, json={"transcription": TRANSCRIPTION, "use_examples": False}
        )
        assert response.status_code == 200
        assert "EXAMPLE 1" not in call_log[0]["system_prompt"]

    def test_evaluate_false_omits_validation(self, client: TestClient, call_log: list[dict]) -> None:
        response = client.post(
            ESTIMATE_URL, json={"transcription": TRANSCRIPTION, "evaluate": False}
        )
        assert response.status_code == 200
        assert response.json()["validation"] is None

    def test_missing_usage_returns_null_usage_and_cost(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake(*args: object, **kwargs: object) -> dict:
            return {
                "estimation": "## Estimation: No Usage",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "finish_reason": "stop",
            }

        monkeypatch.setattr(llm_service, "generate_estimation", fake)
        response = client.post(ESTIMATE_URL, json={"transcription": TRANSCRIPTION})
        assert response.status_code == 200
        body = response.json()
        assert body["usage"] is None
        assert body["estimated_cost_usd"] is None
        assert "generated_at" in body
