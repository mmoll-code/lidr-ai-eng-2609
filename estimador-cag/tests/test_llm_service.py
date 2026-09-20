"""Unit tests for the LLM estimation service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.context.examples import ESTIMATION_EXAMPLES
from app.services.llm_service import (
    LlmConfigurationError,
    build_system_prompt,
    generate_estimation,
)


class TestBuildSystemPrompt:
    def test_includes_role_and_examples(self) -> None:
        prompt = build_system_prompt()

        assert "expert software estimator" in prompt.lower()
        assert "Example 1" in prompt
        assert "Example 2" in prompt
        assert "Meeting summary" in prompt
        assert "Estimation" in prompt

        for example in ESTIMATION_EXAMPLES:
            assert example["meeting_summary"].strip()[:40] in prompt


class TestGenerateEstimation:
    @pytest.mark.asyncio
    async def test_rejects_empty_transcription(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await generate_estimation("")

        with pytest.raises(ValueError, match="empty"):
            await generate_estimation("   ")

    @pytest.mark.asyncio
    async def test_openai_returns_estimation(self) -> None:
        mock_choice = MagicMock()
        mock_choice.message.content = "## Estimation: Test Project\nTotal: 100 hours"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncOpenAI",
                return_value=mock_client,
            ) as mock_openai_cls,
        ):
            mock_settings.llm_provider = "openai"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.openai_api_key = "test-key"

            result = await generate_estimation(
                "Client needs a CRM with contacts and deals."
            )

        assert result == "## Estimation: Test Project\nTotal: 100 hours"
        mock_openai_cls.assert_called_once_with(api_key="test-key")
        create_kwargs = mock_client.chat.completions.create.await_args.kwargs
        assert create_kwargs["model"] == "gpt-4o-mini"
        messages = create_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "expert software estimator" in messages[0]["content"].lower()
        assert messages[1]["role"] == "user"
        assert "Client needs a CRM with contacts and deals." in messages[1]["content"]

    @pytest.mark.asyncio
    async def test_missing_openai_api_key_raises(self) -> None:
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.openai_api_key = ""

            with pytest.raises(LlmConfigurationError, match="OpenAI API key"):
                await generate_estimation("Some transcription")

    @pytest.mark.asyncio
    async def test_unsupported_provider_raises(self) -> None:
        with patch("app.services.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "unknown"
            mock_settings.llm_model = "some-model"

            with pytest.raises(LlmConfigurationError, match="Unsupported LLM provider"):
                await generate_estimation("Some transcription")

    @pytest.mark.asyncio
    async def test_anthropic_returns_estimation(self) -> None:
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "## Estimation: Accounting Platform\nTotal: 80 hours"
        mock_response = MagicMock()
        mock_response.content = [mock_block]

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with (
            patch("app.services.llm_service.settings") as mock_settings,
            patch(
                "app.services.llm_service.AsyncAnthropic",
                return_value=mock_client,
            ) as mock_anthropic_cls,
        ):
            mock_settings.llm_provider = "anthropic"
            mock_settings.llm_model = "claude-3-5-sonnet-20240620"
            mock_settings.anthropic_api_key = "test-anthropic-key"

            result = await generate_estimation(
                "Client needs an accounting portal."
            )

        assert result == "## Estimation: Accounting Platform\nTotal: 80 hours"
        mock_anthropic_cls.assert_called_once_with(api_key="test-anthropic-key")
        create_kwargs = mock_client.messages.create.await_args.kwargs
        assert create_kwargs["model"] == "claude-3-5-sonnet-20240620"
        assert "expert software estimator" in create_kwargs["system"].lower()
        assert "Client needs an accounting portal." in create_kwargs["messages"][0][
            "content"
        ]
