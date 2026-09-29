"""Unit tests for the Streamlit UI API client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from ui.api_client import (
    Estimation,
    EstimationInput,
    EstimatorApiError,
    request_estimation,
    stream_estimation,
)

DESCRIPTION = "Client needs a CRM with contacts and role-based access."


def _input(**overrides: str) -> EstimationInput:
    data = {
        "description": DESCRIPTION,
        "project_type": "web_saas",
        "detail_level": "medium",
        "output_format": "phases_table",
    }
    data.update(overrides)
    return EstimationInput(**data)


def _success_payload() -> dict:
    return {"text": "## Estimation: CRM\nTotal: 100 hours", "prompt_version": "v1"}


class TestRequestEstimation:
    def test_maps_successful_response(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = _success_payload()
        mock_response.raise_for_status = MagicMock()

        with patch("ui.api_client.httpx.post", return_value=mock_response) as mock_post:
            result = request_estimation(_input())

        assert isinstance(result, Estimation)
        assert result.text == "## Estimation: CRM\nTotal: 100 hours"
        assert result.prompt_version == "v1"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs.args[0].endswith("/api/v1/estimate")
        assert call_kwargs.kwargs["json"] == {
            "description": DESCRIPTION,
            "project_type": "web_saas",
            "detail_level": "medium",
            "output_format": "phases_table",
        }

    def test_rejects_short_description_before_request(self) -> None:
        with patch("ui.api_client.httpx.post") as mock_post:
            with pytest.raises(ValueError, match="20"):
                request_estimation(_input(description="too short"))

            with pytest.raises(ValueError, match="20"):
                request_estimation(_input(description="   "))

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

        with (
            patch("ui.api_client.httpx.post", return_value=mock_response),
            pytest.raises(EstimatorApiError, match="not configured"),
        ):
            request_estimation(_input())

    def test_502_raises_estimator_api_error(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.json.return_value = {"detail": "Upstream LLM call failed"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Gateway",
            request=MagicMock(),
            response=mock_response,
        )

        with (
            patch("ui.api_client.httpx.post", return_value=mock_response),
            pytest.raises(EstimatorApiError, match="failed"),
        ):
            request_estimation(_input())

    def test_connect_error_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(EstimatorApiError, match="connect"):
            request_estimation(_input())

    def test_timeout_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.post",
            side_effect=httpx.TimeoutException("Timed out"),
        ), pytest.raises(EstimatorApiError, match="timed out"):
            request_estimation(_input())


class TestStreamEstimation:
    def test_yields_token_payloads_and_stops_on_done(self) -> None:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.iter_lines.return_value = [
            "event: token",
            "data: Hello ",
            "data: world",
            "",
            "event: token",
            "data: ## Title",
            "data: ",
            "data: Body",
            "",
            "event: done",
            "data: [DONE]",
            "",
        ]
        stream_cm = MagicMock()
        stream_cm.__enter__.return_value = response
        stream_cm.__exit__.return_value = False

        with patch("ui.api_client.httpx.stream", return_value=stream_cm) as mock_stream:
            chunks = list(stream_estimation(_input()))

        assert chunks == ["Hello \nworld", "## Title\n\nBody"]
        assert mock_stream.call_args.args[0] == "POST"
        assert mock_stream.call_args.args[1].endswith("/api/v1/estimate/stream")
        assert mock_stream.call_args.kwargs["json"]["description"] == DESCRIPTION

    def test_error_event_raises_estimator_api_error(self) -> None:
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.iter_lines.return_value = [
            "event: error",
            "data: provider down",
            "",
        ]
        stream_cm = MagicMock()
        stream_cm.__enter__.return_value = response
        stream_cm.__exit__.return_value = False

        with (
            patch("ui.api_client.httpx.stream", return_value=stream_cm),
            pytest.raises(EstimatorApiError, match="provider down"),
        ):
            list(stream_estimation(_input()))

    def test_connect_error_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.stream",
            side_effect=httpx.ConnectError("Connection refused"),
        ), pytest.raises(EstimatorApiError, match="connect"):
            list(stream_estimation(_input()))

    def test_timeout_raises_estimator_api_error(self) -> None:
        with patch(
            "ui.api_client.httpx.stream",
            side_effect=httpx.TimeoutException("Timed out"),
        ), pytest.raises(EstimatorApiError, match="timed out"):
            list(stream_estimation(_input()))
