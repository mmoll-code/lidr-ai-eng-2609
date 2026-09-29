"""HTTP client for the Estimator API."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from ui.config import ui_settings

MIN_DESCRIPTION_LENGTH = 20


class EstimatorApiError(Exception):
    """Raised when the Estimator API request fails."""


@dataclass(frozen=True)
class EstimationInput:
    description: str
    project_type: str
    detail_level: str
    output_format: str


@dataclass(frozen=True)
class Estimation:
    text: str
    prompt_version: str


def stream_estimation(estimation_input: EstimationInput) -> Iterator[str]:
    """POST to the SSE endpoint and yield text chunks as they arrive."""
    payload = _payload(estimation_input)
    url = f"{ui_settings.estimator_api_url.rstrip('/')}/api/v1/estimate/stream"
    timeout = ui_settings.estimator_request_timeout_seconds

    try:
        with httpx.stream(
            "POST",
            url,
            json=payload,
            timeout=timeout,
            headers={"Accept": "text/event-stream"},
        ) as response:
            response.raise_for_status()
            yield from _iter_sse_tokens(response)
    except httpx.ConnectError as exc:
        raise EstimatorApiError(
            "Could not connect to the Estimator API. Is the server running?"
        ) from exc
    except httpx.TimeoutException as exc:
        raise EstimatorApiError("The Estimator API request timed out. Try again later.") from exc
    except httpx.HTTPStatusError as exc:
        raise EstimatorApiError(_message_for_status(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise EstimatorApiError(f"Estimator API request failed: {exc}") from exc


def _iter_sse_tokens(response: httpx.Response) -> Iterator[str]:
    """Parse SSE messages. Multiple data lines in one message join with newlines."""
    current_event = "token"
    data_lines: list[str] = []
    for raw_line in response.iter_lines():
        if raw_line == "":
            if data_lines:
                payload_text = "\n".join(data_lines)
                data_lines = []
                if current_event == "token":
                    yield payload_text
                elif current_event == "error":
                    raise EstimatorApiError(payload_text)
                elif current_event == "done":
                    return
            current_event = "token"
            continue
        if raw_line.startswith("event:"):
            current_event = raw_line[6:].strip()
        elif raw_line.startswith("data:"):
            data_lines.append(raw_line[6:] if raw_line.startswith("data: ") else raw_line[5:])


def request_estimation(estimation_input: EstimationInput) -> Estimation:
    """Request a software estimation from the Estimator API."""
    payload = _payload(estimation_input)
    url = f"{ui_settings.estimator_api_url.rstrip('/')}/api/v1/estimate"
    timeout = ui_settings.estimator_request_timeout_seconds

    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise EstimatorApiError(
            "Could not connect to the Estimator API. Is the server running?"
        ) from exc
    except httpx.TimeoutException as exc:
        raise EstimatorApiError(
            "The Estimator API request timed out. Try again later."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise EstimatorApiError(_message_for_status(exc.response)) from exc
    except httpx.HTTPError as exc:
        raise EstimatorApiError(f"Estimator API request failed: {exc}") from exc

    return _parse_estimation(response.json())


def _payload(estimation_input: EstimationInput) -> dict[str, str]:
    description = estimation_input.description.strip()
    if len(description) < MIN_DESCRIPTION_LENGTH:
        raise ValueError("Description must be at least 20 characters")
    return {
        "description": description,
        "project_type": estimation_input.project_type,
        "detail_level": estimation_input.detail_level,
        "output_format": estimation_input.output_format,
    }


def _message_for_status(response: httpx.Response) -> str:
    detail = _extract_detail(response)
    if response.status_code == 503:
        return detail or "LLM provider is not configured correctly"
    if response.status_code == 502:
        return detail or "Upstream LLM call failed"
    if detail:
        return f"Estimator API error ({response.status_code}): {detail}"
    return f"Estimator API error ({response.status_code})"


def _extract_detail(response: httpx.Response) -> str | None:
    try:
        payload: Any = response.json()
    except ValueError:
        return None
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
    return None


def _parse_estimation(payload: dict[str, Any]) -> Estimation:
    return Estimation(
        text=str(payload["text"]),
        prompt_version=str(payload["prompt_version"]),
    )
