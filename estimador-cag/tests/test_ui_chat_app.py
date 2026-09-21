"""Unit and AppTest coverage for the Streamlit chat UI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from streamlit.testing.v1 import AppTest

from ui.api_client import Estimation
from ui.chat_app import build_usage_caption

CHAT_APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "chat_app.py"


def _sample_estimation(**overrides: object) -> Estimation:
    data: dict[str, object] = {
        "content": "## Estimation: CRM\nTotal: 100 hours",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "estimated_cost_usd": 0.000045,
        "total_tokens": 150,
    }
    data.update(overrides)
    return Estimation(**data)  # type: ignore[arg-type]


def _success_response(estimation: Estimation) -> MagicMock:
    payload = {
        "estimation": estimation.content,
        "model": estimation.model,
        "provider": estimation.provider,
        "usage": (
            {
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": estimation.total_tokens,
            }
            if estimation.total_tokens is not None
            else None
        ),
        "estimated_cost_usd": estimation.estimated_cost_usd,
        "generated_at": "2026-03-22T13:00:00+00:00",
    }
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status = MagicMock()
    return response


def _run_chat_app() -> AppTest:
    return AppTest.from_file(str(CHAT_APP_PATH)).run()


class TestBuildUsageCaption:
    def test_includes_provider_model_tokens_and_cost(self) -> None:
        caption = build_usage_caption(_sample_estimation())

        assert "openai" in caption
        assert "gpt-4o-mini" in caption
        assert "150" in caption
        assert "0.000045" in caption

    def test_omits_missing_optional_fields(self) -> None:
        caption = build_usage_caption(
            _sample_estimation(estimated_cost_usd=None, total_tokens=None)
        )

        assert "openai" in caption
        assert "gpt-4o-mini" in caption
        assert "tokens" not in caption.lower()
        assert "$" not in caption


class TestChatApp:
    def test_submission_produces_user_and_assistant_messages(self) -> None:
        estimation = _sample_estimation()

        with patch(
            "ui.api_client.httpx.post",
            return_value=_success_response(estimation),
        ) as mock_post:
            at = _run_chat_app()
            at.chat_input[0].set_value("Client needs a CRM.").run()

        assert not at.exception
        assert len(at.chat_message) == 2
        assert at.chat_message[0].name == "user"
        assert at.chat_message[1].name == "assistant"
        assert "Client needs a CRM." in at.chat_message[0].markdown[0].value
        assert "Estimation: CRM" in at.chat_message[1].markdown[0].value
        mock_post.assert_called_once()
        assert mock_post.call_args.kwargs["json"] == {
            "transcription": "Client needs a CRM."
        }

    def test_history_persists_across_submissions(self) -> None:
        first = _sample_estimation(content="## Estimation: First")
        second = _sample_estimation(content="## Estimation: Second")

        with patch(
            "ui.api_client.httpx.post",
            side_effect=[_success_response(first), _success_response(second)],
        ):
            at = _run_chat_app()
            at.chat_input[0].set_value("First transcription").run()
            at.chat_input[0].set_value("Second transcription").run()

        assert not at.exception
        assert len(at.chat_message) == 4
        assert at.chat_message[0].name == "user"
        assert "First transcription" in at.chat_message[0].markdown[0].value
        assert at.chat_message[1].name == "assistant"
        assert "Estimation: First" in at.chat_message[1].markdown[0].value
        assert at.chat_message[2].name == "user"
        assert "Second transcription" in at.chat_message[2].markdown[0].value
        assert at.chat_message[3].name == "assistant"
        assert "Estimation: Second" in at.chat_message[3].markdown[0].value

    def test_api_error_renders_without_losing_history(self) -> None:
        with patch(
            "ui.api_client.httpx.post",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            at = _run_chat_app()
            at.chat_input[0].set_value("Some transcription").run()

        assert not at.exception
        assert len(at.chat_message) == 2
        assert at.chat_message[0].name == "user"
        assert at.chat_message[1].name == "assistant"
        assert len(at.error) == 1
        assert "Could not connect" in at.error[0].value
