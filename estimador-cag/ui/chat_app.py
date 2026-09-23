"""Streamlit chat UI for software effort estimation."""

import sys
from pathlib import Path

# streamlit run adds this file's directory to sys.path, not the project root.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from ui.api_client import Estimation, EstimatorApiError, request_estimation


def build_usage_caption(estimation: Estimation) -> str:
    """Build a short caption with provider, model, and optional usage stats."""
    parts = [estimation.provider, estimation.model]
    if estimation.total_tokens is not None:
        parts.append(f"{estimation.total_tokens} tokens")
    if estimation.estimated_cost_usd is not None:
        parts.append(f"~${estimation.estimated_cost_usd:.6f}")
    return " · ".join(parts)


def _ensure_message_history() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []


def _render_history() -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            caption = message.get("caption")
            if caption:
                st.caption(caption)


def main() -> None:
    st.set_page_config(page_title="Estimador CAG", page_icon="📐")
    st.title("Estimador CAG")
    st.caption(
        "Paste a meeting transcription to get a software effort estimation."
    )

    _ensure_message_history()
    _render_history()

    prompt = st.chat_input("Paste the meeting transcription...")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Generating estimation..."):
                estimation = request_estimation(prompt)
            st.markdown(estimation.content)
            caption = build_usage_caption(estimation)
            st.caption(caption)
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": estimation.content,
                    "caption": caption,
                }
            )
        except EstimatorApiError as exc:
            error_text = str(exc)
            st.error(error_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_text}
            )
        except ValueError as exc:
            error_text = str(exc)
            st.error(error_text)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_text}
            )


if __name__ == "__main__":
    main()
