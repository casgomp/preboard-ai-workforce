"""Chat UI — Databricks App entry point (PR1c).

Streamlit is one of the frameworks Databricks Apps supports natively, so this file
runs unmodified both locally (`streamlit run app.py`) and once deployed. Access is
via a `?token=` link (see preboard.auth) — there is no login form, matching
NOTES.md invariant §1.5.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from preboard.auth import InvalidToken, verify_token  # noqa: E402
from preboard.qa import QA, Answer, Handoff  # noqa: E402
from preboard.wiring import build_generator, build_retriever, has_databricks_credentials  # noqa: E402
from preboard.store import MissLog  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "misses.db"

st.set_page_config(page_title="preboard", page_icon="📋")
# Cheap insurance against a repeat of the credential-detection bug (NOTES.md §12):
# this line is the only way to notice a silent fallback to stub mode without SSO'ing
# into the app to look at the UI caption — `databricks apps logs` shows it directly.
print(f"[preboard] real Databricks components: {has_databricks_credentials()}")


@st.cache_resource
def get_qa() -> QA:
    retriever, confidence_threshold = build_retriever(CORPUS_DIR)
    return QA(
        retriever=retriever,
        generator=build_generator(),
        miss_log=MissLog(DB_PATH),
        confidence_threshold=confidence_threshold,
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
    if not has_databricks_credentials():
        st.caption(":gray[Running in local stub mode — no Databricks credentials configured.]")

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
        sources = "; ".join(f"{c.source_doc} — {c.source_section}" for c in result.citations)
        reply = f"{result.text}\n\n*Source: {sources}*"
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
