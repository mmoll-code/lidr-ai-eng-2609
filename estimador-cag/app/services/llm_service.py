"""Estimation orchestration: prompt building, optional preprocessing, and dispatch to the LLM."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

from app.config import Settings, get_settings
from app.context.examples import format_examples_for_prompt, select_examples
from app.dependencies import get_llm_wrapper
from app.schemas.estimations import ExampleFormat, PreprocessingMode

log = structlog.get_logger()

DEFAULT_MAX_TOKENS = 4000
EXTRACTION_MAX_TOKENS = 1500


class LlmConfigurationError(Exception):
    """Raised when the LLM provider or credentials are misconfigured."""


class LLMServiceError(Exception):
    """Raised when the LLM provider call fails."""


PROMPT_OUTPUT_BASIC = "Generate an estimation for the project described above."

PROMPT_OUTPUT_STRUCTURED = """\
Generate the estimation with this exact structure:

## Project summary
[2-3 sentences describing the project scope and goals]

## Task breakdown
| Task | Hours | Cost (EUR) |
[one row per task; cost = hours * 62.50 EUR for developer tasks]

## Totals
- Total hours: [number]
- Total cost: [number] EUR
- Recommended team: [composition]
- Estimated duration: [weeks]

## Risks and assumptions
- [3-5 bullet points covering technical risks, scope assumptions, and external dependencies]
"""

ACTIVE_OUTPUT_PROMPT = PROMPT_OUTPUT_BASIC

INLINE_CLEANING_BLOCK = """\
The transcription you receive is from a real meeting and may contain:
- Informal small talk you must ignore
- Implicit requirements you must surface explicitly
- Contradictions where you must trust the most recent statement
- Non-technical jargon you must interpret

Extract ONLY the functional and technical requirements relevant to the estimation."""

EXTRACTION_SYSTEM_PROMPT = (
    "You are an analyst. Read the meeting transcription and produce a clean, "
    "deduplicated bullet list of functional requirements, non-functional "
    "requirements, integrations, constraints and explicit deadlines. Ignore "
    "fillers, divagations and off-topic remarks. Output Markdown only."
)


@dataclass
class GenerationOptions:
    """Per-request knobs that drive prompt construction and the LLM call."""

    preprocessing: PreprocessingMode = "none"
    example_format: ExampleFormat = "markdown"
    num_examples: int = 3
    use_examples: bool = True
    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    thinking_budget: int | None = None


def build_system_prompt(
    example_format: ExampleFormat = "markdown",
    num_examples: int = 3,
    use_examples: bool = True,
    inline_cleaning: bool = False,
) -> str:
    """Assemble the system prompt with role, rates, output spec and examples."""
    role = (
        "You are a senior software consultant with 15+ years of experience in project "
        "estimation. Your task is to produce a detailed software project estimation based "
        "on a meeting transcription provided by the user."
    )
    rates = (
        "Use a developer rate of approximately 62.50 EUR/hour (500 EUR/day) and a designer "
        "rate of approximately 50 EUR/hour (400 EUR/day). Provide realistic, well-justified "
        "numbers."
    )

    examples_block = ""
    if use_examples and num_examples > 0:
        rendered = format_examples_for_prompt(select_examples(num_examples), example_format)
        if rendered:
            examples_block = (
                "Below are reference estimations from previous projects. Use them as a guide "
                "for structure, level of detail, and realistic pricing. Adapt the content to "
                "match the specific project described in the transcription.\n\n"
                + rendered
            )

    cleaning_block = INLINE_CLEANING_BLOCK if inline_cleaning else ""
    sections = [role, cleaning_block, rates, ACTIVE_OUTPUT_PROMPT, examples_block]
    return "\n\n".join(section for section in sections if section)


def _require_api_key(current: Settings) -> None:
    if not current.openai_api_key and not current.anthropic_api_key:
        raise LlmConfigurationError(
            "At least one of OPENAI_API_KEY or ANTHROPIC_API_KEY must be set"
        )


def _invoke_llm(
    *,
    system_prompt: str,
    user_message: str,
    model_override: str | None,
    max_tokens: int,
    thinking_budget: int | None,
) -> dict[str, Any]:
    """Single seam through which every LLM call passes. Tests monkeypatch this."""
    _require_api_key(get_settings())
    wrapper = get_llm_wrapper()
    return wrapper.complete(
        system_prompt=system_prompt,
        user_message=user_message,
        model_override=model_override,
        max_tokens=max_tokens,
        thinking_budget=thinking_budget,
    )


def extract_requirements(
    transcription: str,
    opts: GenerationOptions,
) -> tuple[str, dict, float]:
    """Run the phase-1 call that turns a raw transcription into clean requirements."""
    log.info("extracting_requirements", model_override=opts.model)
    result = _invoke_llm(
        system_prompt=EXTRACTION_SYSTEM_PROMPT,
        user_message=transcription,
        model_override=opts.model,
        max_tokens=EXTRACTION_MAX_TOKENS,
        thinking_budget=None,
    )
    return (
        result["estimation"],
        {
            "input": result["usage"]["input_tokens"],
            "output": result["usage"]["output_tokens"],
        },
        float(result.get("estimated_cost_usd") or 0.0),
    )


def generate_estimation(
    transcription: str,
    opts: GenerationOptions | None = None,
) -> dict[str, Any]:
    """Generate a software estimation from a meeting transcription."""
    if not transcription or not transcription.strip():
        raise ValueError("Transcription must not be empty")

    opts = opts or GenerationOptions()
    started = time.perf_counter()

    prep_usage = {"input": 0, "output": 0}
    prep_cost = 0.0
    extracted_requirements: str | None = None
    user_input = transcription

    if opts.preprocessing == "two_phase":
        extracted_requirements, prep_usage, prep_cost = extract_requirements(transcription, opts)
        user_input = extracted_requirements

    system_prompt = build_system_prompt(
        example_format=opts.example_format,
        num_examples=opts.num_examples,
        use_examples=opts.use_examples,
        inline_cleaning=(opts.preprocessing == "inline_cleaning"),
    )

    log.info(
        "generating_estimation",
        model_override=opts.model,
        preprocessing=opts.preprocessing,
        example_format=opts.example_format,
        num_examples=opts.num_examples,
        use_examples=opts.use_examples,
        max_tokens=opts.max_tokens,
        thinking_budget=opts.thinking_budget,
    )

    try:
        result = _invoke_llm(
            system_prompt=system_prompt,
            user_message=user_input,
            model_override=opts.model,
            max_tokens=opts.max_tokens,
            thinking_budget=opts.thinking_budget,
        )
    except LlmConfigurationError:
        raise
    except Exception as exc:
        log.error("llm_call_failed", error=str(exc), error_type=type(exc).__name__)
        raise LLMServiceError(f"LLM call failed: {exc}") from exc

    result["usage"]["preprocessing_input_tokens"] = prep_usage["input"]
    result["usage"]["preprocessing_output_tokens"] = prep_usage["output"]
    result["preprocessing"] = opts.preprocessing
    result["extracted_requirements"] = extracted_requirements
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    result["estimated_cost_usd"] = round(
        float(result.get("estimated_cost_usd") or 0.0) + prep_cost, 6
    )
    result.setdefault("cache_hit", False)
    return result
