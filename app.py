"""Chat UI — Databricks App entry point (PR1c).

Streamlit is one of the frameworks Databricks Apps supports natively, so this file
runs unmodified both locally (`streamlit run app.py`) and once deployed. Access is
via a `?token=` link (see preboard.auth) — there is no login form, matching
NOTES.md invariant §1.5.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from preboard.auth import InvalidToken, verify_token  # noqa: E402
from preboard.gap_report import gap_report  # noqa: E402
from preboard.handoff import handoff_target  # noqa: E402
from preboard.offers import offer_info  # noqa: E402
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


def show_gap_report() -> None:
    """Second view (`?view=gaps`), not behind the offer token: this is an internal HR
    view, not part of the candidate-facing flow, and misses.db lives in this
    container's local filesystem, so it's only reachable this way, not via the CLI,
    once deployed (NOTES.md §15)."""
    st.title("preboard — gap report")
    st.caption("Aggregated across all candidates; no per-cohort breakdown (NOTES.md §2).")
    entries = gap_report(MissLog(DB_PATH))
    if not entries:
        st.info("No misses logged yet.")
        return
    st.dataframe(
        [
            {
                "question": e.example_question,
                "count": e.count,
                "distinct offers": e.distinct_offers,
                "last seen": e.last_seen,
            }
            for e in entries
        ],
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    if st.query_params.get("view") == "gaps":
        show_gap_report()
        return

    st.title("preboard")
    st.caption("Ask about your offer. Answers are grounded in your offer packet and cite their source.")
    if not has_databricks_credentials():
        st.caption(":gray[Running in local stub mode — no Databricks credentials configured.]")

    offer_id = resolve_offer_id()
    if offer_id is None:
        return

    info = offer_info(offer_id)
    if info is not None:
        delta = (info.start_date - date.today()).days
        if delta > 0:
            st.caption(f"You start in {delta} days ({info.start_date:%B %d, %Y}).")
        elif delta == 0:
            st.caption("You start today!")
        else:
            st.caption(f"You started {info.start_date:%B %d, %Y}.")

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

    try:
        result = get_qa().ask(offer_id, question)
    except Exception as exc:  # noqa: BLE001 — degrade to a handoff, never a traceback on stage
        print(f"[preboard] error answering question for {offer_id!r}: {exc!r}")
        target = handoff_target(offer_id)
        reply = (
            "Something went wrong answering that, so I don't want to guess. I've flagged it "
            f"for **{target.name}** ({target.contact}), who will follow up with you directly."
        )
    else:
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
