"""HTTP tests for the estimation endpoint."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_llm_wrapper
from app.main import app

ESTIMATE_URL = "/api/v1/estimate"
VALID_PAYLOAD = {
    "description": "A small B2B SaaS to manage employee equipment loans across teams.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table",
}


class FakeWrapper:
    """Records ``complete`` kwargs and returns a canned wrapper result."""

    def __init__(self, response_text: str = "fake estimation") -> None:
        self.response_text = response_text
        self.calls: list[dict[str, Any]] = []

    def complete(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {"estimation": self.response_text}


class BoomWrapper:
    def complete(self, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("connection reset")


@pytest.fixture
def fake_wrapper() -> FakeWrapper:
    wrapper = FakeWrapper()
    app.dependency_overrides[get_llm_wrapper] = lambda: wrapper
    yield wrapper
    app.dependency_overrides.pop(get_llm_wrapper, None)


class TestCreateEstimation:
    def test_valid_payload_returns_text_and_prompt_version(
        self, client: TestClient, fake_wrapper: FakeWrapper
    ) -> None:
        response = client.post(ESTIMATE_URL, json=VALID_PAYLOAD)

        assert response.status_code == 200
        body = response.json()
        assert body["text"] == "fake estimation"
        assert body["prompt_version"] == "v1"
        assert set(body) == {"text", "prompt_version"}

    def test_endpoint_passes_separate_system_and_user_messages(
        self, client: TestClient, fake_wrapper: FakeWrapper
    ) -> None:
        client.post(ESTIMATE_URL, json=VALID_PAYLOAD)

        assert len(fake_wrapper.calls) == 1
        call = fake_wrapper.calls[0]
        assert "system_prompt" in call
        assert "user_message" in call
        assert VALID_PAYLOAD["description"] in call["user_message"]
        assert VALID_PAYLOAD["description"] not in call["system_prompt"]
        assert "senior project estimator" in call["system_prompt"].lower()
        assert "<project_description>" in call["user_message"]

    def test_short_description_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "description": "too short"}
        response = client.post(ESTIMATE_URL, json=payload)
        assert response.status_code == 422

    def test_missing_project_type_returns_422(self, client: TestClient) -> None:
        payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "project_type"}
        response = client.post(ESTIMATE_URL, json=payload)
        assert response.status_code == 422

    def test_unknown_enum_returns_422(self, client: TestClient) -> None:
        payload = {**VALID_PAYLOAD, "output_format": "definitely_not_real"}
        response = client.post(ESTIMATE_URL, json=payload)
        assert response.status_code == 422

    def test_provider_failure_returns_502(self, client: TestClient) -> None:
        app.dependency_overrides[get_llm_wrapper] = lambda: BoomWrapper()
        try:
            response = client.post(ESTIMATE_URL, json=VALID_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_llm_wrapper, None)

        assert response.status_code == 502
        assert "failed" in response.json()["detail"].lower()
