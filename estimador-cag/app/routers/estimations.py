"""Estimation HTTP endpoints."""

import asyncio
from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_llm_wrapper
from app.prompts import render_estimation_prompt
from app.schemas.estimations import EstimationRequest, EstimationResponse
from app.services.llm_wrapper import LLMWrapper

log = structlog.get_logger()

router = APIRouter(tags=["estimations"])
_llm_wrapper = Depends(get_llm_wrapper)

PROMPT_VERSION = "v1"


@router.post(
    "/estimate",
    response_model=EstimationResponse,
    summary="Generate a software effort estimation",
    description=(
        "Accepts a project description plus project type, detail level, and "
        "output format, then returns a free-text estimation from the configured LLM."
    ),
    responses={502: {"description": "Upstream LLM call failed"}},
)
async def create_estimation(
    request: EstimationRequest,
    wrapper: LLMWrapper = _llm_wrapper,
) -> EstimationResponse:
    """Render the versioned prompt pair and ask the LLM for an estimation."""
    system_prompt, user_message = render_estimation_prompt(request, version=PROMPT_VERSION)

    log.info(
        "estimation_request_received",
        prompt_version=PROMPT_VERSION,
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
        description_chars=len(request.description),
    )

    try:
        result = wrapper.complete(system_prompt=system_prompt, user_message=user_message)
    except Exception as exc:
        log.error("estimation_endpoint_error", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(status_code=502, detail="Upstream LLM call failed") from exc

    return EstimationResponse(text=result["estimation"], prompt_version=PROMPT_VERSION)


@router.post("/estimate/stream")
async def create_estimation_stream(
    request: EstimationRequest,
    wrapper: LLMWrapper = _llm_wrapper,
) -> EventSourceResponse:
    """Stream a software estimation token by token via Server-Sent Events."""
    system_prompt, user_message = render_estimation_prompt(request, version=PROMPT_VERSION)

    log.info(
        "estimation_stream_request_received",
        prompt_version=PROMPT_VERSION,
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
        description_chars=len(request.description),
    )

    async def event_generator() -> AsyncIterator[dict]:
        loop = asyncio.get_running_loop()
        chunks = wrapper.complete_stream(system_prompt=system_prompt, user_message=user_message)

        def _next_chunk() -> str | None:
            try:
                return next(chunks)
            except StopIteration:
                return None
            except Exception as exc:
                log.error(
                    "estimate_stream_failed",
                    error=str(exc),
                    error_type=type(exc).__name__,
                )
                raise

        try:
            while True:
                chunk = await loop.run_in_executor(None, _next_chunk)
                if chunk is None:
                    break
                if chunk:
                    yield {"event": "token", "data": chunk}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as exc:  # noqa: BLE001 — stream failures become an SSE error event
            yield {"event": "error", "data": str(exc)}

    return EventSourceResponse(event_generator())
