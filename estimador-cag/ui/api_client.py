"""HTTP client for the Estimator CAG API."""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import httpx

from ui.config import ui_settings


class EstimatorApiError(Exception):
    """Raised when the Estimator API request fails."""


@dataclass(frozen=True)
class Estimation:
    content: str
    model: str
    provider: str
    estimated_cost_usd: float | None
    total_tokens: int | None


def stream_estimation(transcription: str) -> Iterator[str]:
    """POST to the SSE endpoint and yield text chunks as they arrive."""
    if not transcription or not transcription.strip():
        raise ValueError("Transcription must not be empty")

    url = f"{ui_settings.estimator_api_url.rstrip('/')}/api/v1/estimate/stream"
    timeout = ui_settings.estimator_request_timeout_seconds
    payload = {"transcription": transcription.strip()}

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


def request_estimation(transcription: str) -> Estimation:
    """Request a software estimation from the Estimator API."""
    if not transcription or not transcription.strip():
        raise ValueError("Transcription must not be empty")

    url = f"{ui_settings.estimator_api_url.rstrip('/')}/api/v1/estimate"
    timeout = ui_settings.estimator_request_timeout_seconds

    try:
        response = httpx.post(
            url,
            json={"transcription": transcription.strip()},
            timeout=timeout,
        )
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


def _message_for_status(response: httpx.Response) -> str:
    detail = _extract_detail(response)
    if response.status_code == 503:
        return detail or "LLM provider is not configured correctly"
    if response.status_code == 502:
        return detail or "LLM provider request failed"
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
    usage = payload.get("usage")
    total_tokens: int | None = None
    if isinstance(usage, dict):
        raw_total = usage.get("total_tokens")
        if isinstance(raw_total, int):
            total_tokens = raw_total

    cost = payload.get("estimated_cost_usd")
    estimated_cost_usd = cost if isinstance(cost, (int, float)) else None

    return Estimation(
        content=str(payload["estimation"]),
        model=str(payload["model"]),
        provider=str(payload["provider"]),
        estimated_cost_usd=float(estimated_cost_usd)
        if estimated_cost_usd is not None
        else None,
        total_tokens=total_tokens,
    )
