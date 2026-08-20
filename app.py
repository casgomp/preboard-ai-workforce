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
from preboard.gap_report import department_gap_report, gap_report  # noqa: E402
from preboard.handoff import handoff_target  # noqa: E402
from preboard.qa import QA, Answer, Handoff  # noqa: E402
from preboard.wiring import (  # noqa: E402
    build_generator,
    build_retriever,
    build_router,
    has_databricks_credentials,
)
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
    router, router_threshold = build_router(CORPUS_DIR)
    return QA(
        retriever=retriever,
        generator=build_generator(),
        miss_log=MissLog(DB_PATH),
        confidence_threshold=confidence_threshold,
        router=router,
        router_threshold=router_threshold,
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
    miss_log = MissLog(DB_PATH)

    dept_entries = department_gap_report(miss_log)
    if not dept_entries:
        st.info("No misses logged yet.")
        return

    st.subheader("By department")
    st.caption("Which team's docs need the most work (PR9/NOTES.md §18).")
    st.dataframe(
        [
            {
                "department": d.department,
                "misses": d.count,
                "distinct questions": d.distinct_questions,
                "distinct offers": d.distinct_offers,
                "last seen": d.last_seen,
            }
            for d in dept_entries
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("By question")
    entries = gap_report(miss_log)
    st.dataframe(
        [
            {
                "question": e.example_question,
                "department": e.department or "-",
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

    as_of_raw = st.query_params.get("as_of")
    try:
        as_of = date.fromisoformat(as_of_raw) if as_of_raw else None
    except ValueError:
        as_of = None

    # No countdown caption here anymore (PR12/NOTES.md §19, D5): `preboard/offers.py`
    # is gone, and this Streamlit app has no employee data source of its own to look
    # a start date up from. It's the fallback front end now, not the primary demo
    # surface — the frontend (which does have an employees table) shows the
    # countdown and passes start_date through to server.py's /ask.

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
        result = get_qa().ask(offer_id, question, as_of=as_of)
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
            who = (
                f"the **{result.target.department}** team"
                if result.target.department
                else f"**{result.target.name}**"
            )
            reply = (
                f"I'm not confident enough to answer that from your offer packet, so I've flagged it "
                f"for {who} ({result.target.contact}), who will follow up with you directly."
            )
        else:
            reply = "Something went wrong."

    st.session_state.history.append(("assistant", reply))
    with st.chat_message("assistant"):
        st.markdown(reply)


if __name__ == "__main__":
    main()
