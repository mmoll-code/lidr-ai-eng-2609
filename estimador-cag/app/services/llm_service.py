"""LLM service for CAG-based software estimation."""

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.config import settings
from app.context.examples import ESTIMATION_EXAMPLES


class LlmConfigurationError(Exception):
    """Raised when the LLM provider or credentials are misconfigured."""


def build_system_prompt() -> str:
    """Build the system prompt with role instructions and reference examples."""
    example_sections: list[str] = []
    for index, example in enumerate(ESTIMATION_EXAMPLES, start=1):
        example_sections.append(
            f"### Example {index}\n"
            f"**Meeting summary:**\n{example['meeting_summary'].strip()}\n\n"
            f"**Estimation:**\n{example['estimation'].strip()}"
        )

    examples_block = "\n\n".join(example_sections)

    return (
        "You are an expert software estimator. "
        "You generate software development estimations based on previous examples "
        "and based on a transcription of a new video call.\n\n"
        "Use the reference examples below for format, depth, and level of detail. "
        "Produce a clear task breakdown with hours, recommended team, and duration "
        "when possible.\n\n"
        "## Reference examples\n\n"
        f"{examples_block}"
    )


def _build_user_message(transcription: str) -> str:
    return (
        "Estimate the software development effort for the following video-call "
        "transcription. Follow the format and depth of the reference examples "
        "in the system prompt.\n\n"
        "--- TRANSCRIPTION ---\n"
        f"{transcription.strip()}\n"
        "--- END TRANSCRIPTION ---"
    )


async def _get_completion(system: str, user: str) -> str:
    provider = settings.llm_provider.lower().strip()

    if provider == "openai":
        if not settings.openai_api_key:
            raise LlmConfigurationError("OpenAI API key is not configured")
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise LlmConfigurationError("OpenAI returned an empty completion")
        return content

    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise LlmConfigurationError("Anthropic API key is not configured")
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text_blocks = [
            block.text for block in response.content if block.type == "text"
        ]
        if not text_blocks:
            raise LlmConfigurationError("Anthropic returned an empty completion")
        return "\n".join(text_blocks)

    raise LlmConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")


async def generate_estimation(transcription: str) -> str:
    """Generate a software estimation from a video-call transcription."""
    if not transcription or not transcription.strip():
        raise ValueError("Transcription must not be empty")

    system_prompt = build_system_prompt()
    user_message = _build_user_message(transcription)
    return await _get_completion(system_prompt, user_message)
