"""HTTP tests for the estimation endpoint."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.llm_service import EstimationResult, LlmConfigurationError

ESTIMATE_URL = "/api/v1/estimate"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCreateEstimation:
    @pytest.mark.asyncio
    async def test_returns_estimation_with_usage_and_cost(self, client) -> None:
        mock_result = EstimationResult(
            content="## Estimation: CRM\nTotal: 100 hours",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
        )

        with patch(
            "app.routers.estimations.generate_estimation",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_generate:
            response = await client.post(
                ESTIMATE_URL,
                json={
                    "transcription": "Client needs a CRM with contacts and deals."
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["estimation"] == "## Estimation: CRM\nTotal: 100 hours"
        assert body["model"] == "gpt-4o-mini"
        assert body["provider"] == "openai"
        assert body["usage"]["input_tokens"] == 100
        assert body["usage"]["output_tokens"] == 50
        assert body["usage"]["total_tokens"] == 150
        assert body["estimated_cost_usd"] == 0.000045
        assert "generated_at" in body
        datetime.fromisoformat(body["generated_at"])
        mock_generate.assert_awaited_once_with(
            "Client needs a CRM with contacts and deals."
        )

    @pytest.mark.asyncio
    async def test_missing_transcription_returns_422(self, client) -> None:
        response = await client.post(ESTIMATE_URL, json={})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_transcription_returns_422(self, client) -> None:
        response = await client.post(ESTIMATE_URL, json={"transcription": ""})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_whitespace_transcription_returns_422(self, client) -> None:
        response = await client.post(ESTIMATE_URL, json={"transcription": "   "})
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_llm_configuration_error_returns_503(self, client) -> None:
        with patch(
            "app.routers.estimations.generate_estimation",
            new_callable=AsyncMock,
            side_effect=LlmConfigurationError("OpenAI API key is not configured"),
        ):
            response = await client.post(
                ESTIMATE_URL,
                json={"transcription": "Some transcription"},
            )

        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_provider_failure_returns_502(self, client) -> None:
        with patch(
            "app.routers.estimations.generate_estimation",
            new_callable=AsyncMock,
            side_effect=RuntimeError("connection reset"),
        ):
            response = await client.post(
                ESTIMATE_URL,
                json={"transcription": "Some transcription"},
            )

        assert response.status_code == 502
        assert "failed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_missing_usage_returns_null_usage_and_cost(self, client) -> None:
        mock_result = EstimationResult(
            content="## Estimation: No Usage",
            provider="openai",
            model="gpt-4o-mini",
            input_tokens=None,
            output_tokens=None,
        )

        with patch(
            "app.routers.estimations.generate_estimation",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = await client.post(
                ESTIMATE_URL,
                json={"transcription": "Some transcription"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["estimation"] == "## Estimation: No Usage"
        assert body["usage"] is None
        assert body["estimated_cost_usd"] is None
        assert "generated_at" in body
