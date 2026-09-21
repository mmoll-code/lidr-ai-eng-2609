"""Unit tests for the Streamlit UI API client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ui.api_client import Estimation, EstimatorApiError, request_estimation


def _success_payload() -> dict:
    return {
        "estimation": "## Estimation: CRM\nTotal: 100 hours",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
        },
        "estimated_cost_usd": 0.000045,
        "generated_at": "2026-03-22T13:00:00+00:00",
    }


class TestRequestEstimation:
    def test_maps_successful_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _success_payload()
        mock_response.raise_for_status = MagicMock()

        with patch("ui.api_client.httpx.post", return_value=mock_response) as mock_post:
            result = request_estimation("Client needs a CRM.")

        assert isinstance(result, Estimation)
        assert result.content == "## Estimation: CRM\nTotal: 100 hours"
        assert result.model == "gpt-4o-mini"
        assert result.provider == "openai"
        assert result.estimated_cost_usd == 0.000045
        assert result.total_tokens == 150
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0].endswith("/api/v1/estimate")
        assert call_kwargs.kwargs["json"] == {"transcription": "Client needs a CRM."}

    def test_maps_response_without_usage(self) -> None:
        payload = _success_payload()
        payload["usage"] = None
        payload["estimated_cost_usd"] = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = payload
        mock_response.raise_for_status = MagicMock()

        with patch("ui.api_client.httpx.post", return_value=mock_response):
            result = request_estimation("Some transcription")

        assert result.total_tokens is None
        assert result.estimated_cost_usd is None

    def test_rejects_blank_transcription_before_request(self) -> None:
        with patch("ui.api_client.httpx.post") as mock_post:
            with pytest.raises(ValueError, match="empty"):
                request_estimation("")

            with pytest.raises(ValueError, match="empty"):
                request_estimation("   ")

        mock_post.assert_not_called()

    def test_503_raises_estimator_api_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 503
        mock_response.json.return_value = {
            "detail": "LLM provider is not configured correctly"
        }
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Service Unavailable",
            request=MagicMock(),
            response=mock_response,
        )

        with patch("ui.api_client.httpx.post", return_value=mock_response):
            with pytest.raises(EstimatorApiError, match="not configured"):
                request_estimation("Some transcription")

    def test_502_raises_estimator_api_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.return_value = {"detail": "LLM provider request failed"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=MagicMock(),
            response=mock_response,
        )

        with patch("ui.api_client.httpx.post", return_value=mock_response):
            with pytest.raises(EstimatorApiError, match="request failed"):
                request_estimation("Some transcription")

    def test_connect_error_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(EstimatorApiError, match="connect"):
                request_estimation("Some transcription")

    def test_timeout_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.post",
            side_effect=httpx.TimeoutException("Timed out"),
        ):
            with pytest.raises(EstimatorApiError, match="timed out"):
                request_estimation("Some transcription")
