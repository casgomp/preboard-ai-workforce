"""Chat UI — Databricks App entry point (PR1c).

Streamlit is one of the frameworks Databricks Apps supports natively, so this file
runs unmodified both locally (`streamlit run app.py`) and once deployed. Access is
via a `?token=` link (see preboard.auth) — there is no login form, matching
NOTES.md invariant §1.5.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from preboard.auth import InvalidToken, verify_token
from preboard.generation import StubGenerator
from preboard.qa import QA, Answer, Handoff
from preboard.retrieval import KeywordRetriever
from preboard.store import MissLog

REPO_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "misses.db"

st.set_page_config(page_title="preboard", page_icon="📋")


@st.cache_resource
def get_qa() -> QA:
    return QA(
        retriever=KeywordRetriever(CORPUS_DIR),
        generator=StubGenerator(),
        miss_log=MissLog(DB_PATH),
    )


def resolve_offer_id() -> str | None:
    token = st.query_params.get("token")
    if not token:
        st.error("This link is missing an access token. Ask HR to resend your preboarding link.")
        return None
    try:
        return verify_token(token)
    except InvalidToken:
        st.error("This link is invalid or has expired. Ask HR to resend your preboarding link.")
        return None


def main() -> None:
    st.title("preboard")
    st.caption("Ask about your offer. Answers are grounded in your offer packet and cite their source.")

    offer_id = resolve_offer_id()
    if offer_id is None:
        return

    if "history" not in st.session_state:
        st.session_state.history = []

    for role, content in st.session_state.history:
        with st.chat_message(role):
            st.markdown(content)

    question = st.chat_input("Ask a question about your offer...")
    if not question:
        return

    st.session_state.history.append(("user", question))
    with st.chat_message("user"):
        st.markdown(question)

    result = get_qa().ask(offer_id, question)
    if isinstance(result, Answer):
        reply = f"{result.text}\n\n*Source: {result.source_doc} — {result.source_section}*"
    elif isinstance(result, Handoff):
        reply = (
            "I'm not confident enough to answer that from your offer packet, so I've flagged it "
            f"for **{result.target.name}** ({result.target.contact}), who will follow up with you "
            "directly."
        )
    else:
        reply = "Something went wrong."

    st.session_state.history.append(("assistant", reply))
    with st.chat_message("assistant"):
        st.markdown(reply)


if __name__ == "__main__":
    main()
