"""HTTP boundary onto the same `QA` used by `app.py`/`cli.py` (PR12/NOTES.md §19,
folded in from PLAN_PR11). `frontend/`'s Next.js dev server calls this over
localhost — both processes call the Databricks workspace outward for generation,
embeddings, and Unity Catalog; the workspace is the backend, not this process.

Run with `uvicorn server:app --reload` (needs `DATABRICKS_HOST`/`DATABRICKS_TOKEN`/
`DATABRICKS_WAREHOUSE_ID` or `DATABRICKS_HTTP_PATH` in the environment — see
`.env.example`).

Response shape matches `GroundedAnswer` in `frontend/services/documents/types.ts`
(folded in from PLAN_PR11 D3) rather than inventing a new one, so the UI needs no
render changes from what it already expected of `grounding.ts`.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from preboard.handoff import handoff_target  # noqa: E402
from preboard.qa import QA, Answer, Handoff  # noqa: E402
from preboard.wiring import (  # noqa: E402
    build_generator,
    build_miss_log,
    build_retriever,
    build_router,
    has_databricks_credentials,
)

REPO_ROOT = Path(__file__).resolve().parent
CORPUS_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "misses.db"

# PR11 B3's shape: name the dev port explicitly rather than allow_origins=["*"]
# (rejected by browsers once credentials are involved). Verified locally: `npm run
# dev` actually serves on :3000/:3001 (vinext falls back when 3000 is taken), not
# :5173 as PLAN_PR12's own diagram assumed. In this architecture the browser never
# calls this server directly, though — /api/documents/ask is a Next.js *route
# handler* making a server-to-server fetch — so CORS isn't actually load-bearing on
# the request path this PR wires up; kept as defense-in-depth / for direct testing.
FRONTEND_ORIGIN = "http://localhost:3000"


def _build_qa():
    retriever, confidence_threshold = build_retriever(CORPUS_DIR)
    router, router_threshold = build_router(CORPUS_DIR)
    miss_log = build_miss_log(DB_PATH)
    qa = QA(
        retriever=retriever,
        generator=build_generator(),
        miss_log=miss_log,
        confidence_threshold=confidence_threshold,
        router=router,
        router_threshold=router_threshold,
    )
    return qa, miss_log


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Built once at startup, not per request: EmbeddingRetriever caches chunk
    # embeddings per instance, so a fresh QA per request would re-embed the whole
    # corpus on every question (same reasoning as app.py's @st.cache_resource).
    # miss_log is kept alongside QA (not reached via QA's private _miss_log) so
    # /knowledge-gaps can read it without poking at QA's internals.
    app.state.qa, app.state.miss_log = _build_qa()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    employee_id: str
    question: str
    start_date: date | None = None
    as_of: date | None = None


class Citation(BaseModel):
    documentId: str
    title: str
    excerpt: str


class HandoffInfo(BaseModel):
    department: str
    person: str
    email: str


class GroundedAnswer(BaseModel):
    status: str  # "SUPPORTED" | "NEEDS_HUMAN"
    answer: str
    citations: list[Citation]
    handoff: HandoffInfo | None = None


_EXCERPT_LENGTH = 220


def _truncate(text: str) -> str:
    return text if len(text) <= _EXCERPT_LENGTH else text[:_EXCERPT_LENGTH].rsplit(" ", 1)[0] + "…"


def _handoff_response(target) -> GroundedAnswer:
    return GroundedAnswer(
        status="NEEDS_HUMAN",
        answer=(
            "I'm not confident enough to answer that from the available documents, so "
            f"I've flagged it for {target.department or target.name}, who will follow up "
            "with you directly."
        ),
        citations=[],
        handoff=HandoffInfo(
            department=target.department or target.name, person=target.name, email=target.contact
        ),
    )


@app.post("/ask")
def ask(req: AskRequest) -> GroundedAnswer:
    qa: QA = app.state.qa
    try:
        result = qa.ask(req.employee_id, req.question, start_date=req.start_date, as_of=req.as_of)
    except Exception as exc:  # noqa: BLE001 — degrade to a handoff, never a 500 traceback (app.py's pattern)
        print(f"[server] error answering question for {req.employee_id!r}: {exc!r}")
        return _handoff_response(handoff_target(req.employee_id))

    if isinstance(result, Answer):
        return GroundedAnswer(
            status="SUPPORTED",
            answer=result.text,
            citations=[
                Citation(
                    documentId=c.source_doc,
                    title=c.title or c.source_doc,
                    excerpt=_truncate(c.excerpt or c.source_section),
                )
                for c in result.citations
            ],
        )

    assert isinstance(result, Handoff)
    return _handoff_response(result.target)


@app.get("/health")
def health() -> dict:
    return {"real_components": has_databricks_credentials()}


class DepartmentGap(BaseModel):
    department: str
    count: int
    distinctQuestions: int
    distinctOffers: int
    lastSeen: str


class QuestionGap(BaseModel):
    question: str
    department: str | None
    count: int
    distinctOffers: int
    lastSeen: str


class KnowledgeGaps(BaseModel):
    departments: list[DepartmentGap]
    questions: list[QuestionGap]


@app.get("/knowledge-gaps")
def knowledge_gaps() -> KnowledgeGaps:
    """Backs `frontend`'s HR "Knowledge gaps" panel (ported from
    `feature/fused-preboard`) — the same `question_misses` data `?view=gaps` in
    `app.py` and `gap_report.main()` already show, just as JSON. No HR/candidate
    scoping here: that's the Next.js route's job (`readSession`/`hasCapability`),
    matching how `/ask` leaves auth to the caller (NOTES.md §19, D3)."""
    from preboard.gap_report import department_gap_report, gap_report

    miss_log = app.state.miss_log
    return KnowledgeGaps(
        departments=[
            DepartmentGap(
                department=d.department,
                count=d.count,
                distinctQuestions=d.distinct_questions,
                distinctOffers=d.distinct_offers,
                lastSeen=d.last_seen,
            )
            for d in department_gap_report(miss_log)
        ],
        questions=[
            QuestionGap(
                question=q.example_question,
                department=q.department,
                count=q.count,
                distinctOffers=q.distinct_offers,
                lastSeen=q.last_seen,
            )
            for q in gap_report(miss_log, top_n=20)
        ],
    )
