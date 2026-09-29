"""Unit and AppTest coverage for the Streamlit chat UI."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
from streamlit.testing.v1 import AppTest

from ui.api_client import Estimation
from ui.chat_app import build_usage_caption

CHAT_APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "chat_app.py"
DESCRIPTION = "Client needs a CRM with contacts and role-based access."


def _sample_estimation(**overrides: object) -> Estimation:
    data: dict[str, object] = {
        "text": "## Estimation: CRM\nTotal: 100 hours",
        "prompt_version": "v1",
    }
    data.update(overrides)
    return Estimation(**data)  # type: ignore[arg-type]


def _sse_lines(content: str) -> list[str]:
    lines = ["event: token"]
    for line in content.split("\n"):
        lines.append(f"data: {line}")
    lines.extend(["", "event: done", "data: [DONE]", ""])
    return lines


def _stream_context(content: str) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.iter_lines.return_value = _sse_lines(content)
    context = MagicMock()
    context.__enter__.return_value = response
    context.__exit__.return_value = False
    return context


def _run_chat_app() -> AppTest:
    return AppTest.from_file(str(CHAT_APP_PATH)).run()


class TestBuildUsageCaption:
    def test_includes_prompt_version(self) -> None:
        caption = build_usage_caption(_sample_estimation())
        assert caption == "prompt v1"


class TestChatApp:
    def test_submission_produces_user_and_assistant_messages(self) -> None:
        estimation = _sample_estimation()

        with patch(
            "ui.api_client.httpx.stream",
            return_value=_stream_context(estimation.text),
        ) as mock_stream:
            at = _run_chat_app()
            at.chat_input[0].set_value(DESCRIPTION).run()

        assert not at.exception
        assert len(at.chat_message) == 2
        assert at.chat_message[0].name == "user"
        assert at.chat_message[1].name == "assistant"
        assert DESCRIPTION in at.chat_message[0].markdown[0].value
        assert "Estimation: CRM" in at.chat_message[1].markdown[-1].value
        mock_stream.assert_called_once()
        assert mock_stream.call_args.kwargs["json"] == {
            "description": DESCRIPTION,
            "project_type": "web_saas",
            "detail_level": "medium",
            "output_format": "phases_table",
        }
        labels = [item.label for item in at.sidebar.selectbox]
        assert labels == ["Project type", "Detail level", "Output format"]
        assert any("Primary model" in item.value for item in at.sidebar.markdown)

    def test_history_persists_across_submissions(self) -> None:
        first = _sample_estimation(text="## Estimation: First")
        second = _sample_estimation(text="## Estimation: Second")

        with patch(
            "ui.api_client.httpx.stream",
            side_effect=[_stream_context(first.text), _stream_context(second.text)],
        ):
            at = _run_chat_app()
            at.chat_input[0].set_value("First project: a small inventory tool.").run()
            at.chat_input[0].set_value("Second project: a mobile booking app.").run()

        assert not at.exception
        assert len(at.chat_message) == 4
        assert at.chat_message[0].name == "user"
        assert "First project" in at.chat_message[0].markdown[0].value
        assert at.chat_message[1].name == "assistant"
        assert "Estimation: First" in at.chat_message[1].markdown[-1].value
        assert at.chat_message[2].name == "user"
        assert "Second project" in at.chat_message[2].markdown[0].value
        assert at.chat_message[3].name == "assistant"
        assert "Estimation: Second" in at.chat_message[3].markdown[-1].value

    def test_api_error_renders_without_losing_history(self) -> None:
        with patch(
            "ui.api_client.httpx.stream",
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            at = _run_chat_app()
            at.chat_input[0].set_value(DESCRIPTION).run()

        assert not at.exception
        assert len(at.chat_message) == 2
        assert at.chat_message[0].name == "user"
        assert at.chat_message[1].name == "assistant"
        assert len(at.error) == 1
        assert "Could not connect" in at.error[0].value
