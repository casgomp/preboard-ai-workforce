from datetime import date
from pathlib import Path

import pytest

from preboard.corpus import Chunk, LocalMarkdownSource
from preboard.generation import StubGenerator
from preboard.qa import QA, Answer, Handoff, _tminus_guidance, _TMINUS_OVERDUE_GUIDANCE
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever, RetrievedChunk
from preboard.routing import Router
from preboard.store import MissLog

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"
OFFER_ID = "E001"


@pytest.fixture
def qa(tmp_path):
    return QA(
        retriever=KeywordRetriever(LocalMarkdownSource(CORPUS_DIR)),
        generator=StubGenerator(),
        miss_log=MissLog(tmp_path / "misses.db"),
        confidence_threshold=CONFIDENCE_THRESHOLD,
    )


def test_grounded_answer_names_its_source(qa):
    result = qa.ask(OFFER_ID, "When is my start date?")

    assert isinstance(result, Answer)
    assert result.citations[0].source_doc == OFFER_ID
    assert result.citations[0].source_section == "Start date and first day"
    assert "Wolfsburg" in result.text


def test_low_confidence_hands_off_and_logs_miss(qa):
    result = qa.ask(OFFER_ID, "What's my manager's favorite coffee order?")

    assert isinstance(result, Handoff)
    assert result.target.name == "People Operations"

    misses = qa._miss_log.all_misses()
    assert len(misses) == 1
    assert misses[0].offer_id == OFFER_ID
    assert "coffee" in misses[0].question


def test_unknown_offer_id_with_no_offer_specific_match_hands_off(qa):
    result = qa.ask("someone-else", "When does my signing bonus get paid?")

    assert isinstance(result, Handoff)
    assert result.target.name == "People Operations"


def test_unknown_offer_id_can_still_answer_from_shared_company_content(qa):
    """Not a security gap: company-wide info (corpus.py's SHARED_DOC_ID) isn't
    candidate-specific, so it's fine for it to answer even without a matching offer
    doc — the auth boundary is verify_token(), not this fallback."""
    result = qa.ask("someone-else", "What communication tools do we use?")

    assert isinstance(result, Answer)
    assert result.citations[0].source_doc == "company"


class _FixedRetriever:
    def __init__(self, results):
        self._results = results

    def retrieve(self, offer_id, question):
        return self._results


class _RecordingGenerator:
    def __init__(self):
        self.received_chunks = None

    def generate(self, question, chunks, date_context=None):
        self.received_chunks = chunks
        return "stub answer"


class _FakeDirectorySource:
    """Stands in for `routing.UnityCatalogDirectorySource` (PR12/NOTES.md §19) —
    routing has no local file to read anymore, so QA-level routing tests build their
    own small in-memory `department_contacts`-shaped chunk set instead of hitting the
    network."""

    def load(self, offer_id):
        return [
            Chunk(
                doc_id="directory",
                section="Payroll & Benefits",
                text=(
                    "Person: Julia Hartmann\nContact: payroll@example.com\n"
                    "Covers: pay, tax forms, benefits, commuter and bike expense\n"
                    "Also ask about: bike, expense, payroll"
                ),
            ),
            Chunk(
                doc_id="directory",
                section="IT & Equipment",
                text=(
                    "Person: Michael Braun\nContact: it@example.com\n"
                    "Covers: laptops and equipment\nAlso ask about: laptop, equipment"
                ),
            ),
        ]


def test_broad_question_pulls_in_supporting_chunks_above_score_ratio(tmp_path):
    """Regression: a question spanning multiple sections ("what do I need to do
    before I start?") was answered from only the single top-scored chunk, leaving
    real information out (PR4)."""
    chunks = [Chunk(doc_id="x", section=s, text=s.lower()) for s in "ABCD"]
    results = [
        RetrievedChunk(chunk=chunks[0], score=1.0),
        RetrievedChunk(chunk=chunks[1], score=0.7),  # >= 0.6 * top, included
        RetrievedChunk(chunk=chunks[2], score=0.5),  # < 0.6 * top, excluded
        RetrievedChunk(chunk=chunks[3], score=0.3),
    ]
    generator = _RecordingGenerator()
    qa = QA(
        retriever=_FixedRetriever(results),
        generator=generator,
        miss_log=MissLog(tmp_path / "misses.db"),
        confidence_threshold=0.5,
    )

    result = qa.ask("offer", "question")

    assert isinstance(result, Answer)
    assert {c.section for c in generator.received_chunks} == {"A", "B"}
    assert {c.source_section for c in result.citations} == {"A", "B"}


@pytest.mark.parametrize(
    "delta_days,expected_snippet",
    [
        (60, "More than 8 weeks"),
        (59, "2-8 weeks"),
        (14, "2-8 weeks"),
        (13, "1-2 weeks"),
        (4, "1-2 weeks"),
        (3, _TMINUS_OVERDUE_GUIDANCE),
        (0, _TMINUS_OVERDUE_GUIDANCE),
        (-5, _TMINUS_OVERDUE_GUIDANCE),
    ],
)
def test_tminus_guidance_picks_the_right_band_at_every_boundary(delta_days, expected_snippet):
    assert expected_snippet in _tminus_guidance(delta_days)


def test_date_context_includes_start_date_and_tminus_guidance(qa):
    context = qa._date_context(date(2026, 9, 14), as_of=date(2026, 9, 11))  # 3 days out

    assert "2026-09-11" in context
    assert "in 3 days" in context
    assert _TMINUS_OVERDUE_GUIDANCE in context


def test_date_context_is_none_without_a_start_date(qa):
    """PR12/NOTES.md §19, D5: start_date is supplied by the caller (the frontend's
    employees table), not looked up from a deleted preboard/offers.py — None just
    means the caller had nothing to give, e.g. app.py's local fallback path."""
    assert qa._date_context(None) is None


def _qa_with_router(tmp_path, router_threshold=CONFIDENCE_THRESHOLD):
    return QA(
        retriever=_FixedRetriever([]),
        generator=StubGenerator(),
        miss_log=MissLog(tmp_path / "misses.db"),
        confidence_threshold=CONFIDENCE_THRESHOLD,
        router=Router(KeywordRetriever(_FakeDirectorySource())),
        router_threshold=router_threshold,
    )


def test_low_confidence_question_routes_to_the_matching_department(tmp_path):
    """Regression for the bike question (NOTES.md §17): a low-confidence question
    should reach the right team's contact, not always the same generic fallback."""
    result = _qa_with_router(tmp_path).ask(OFFER_ID, "Can I expense a bike?")

    assert isinstance(result, Handoff)
    assert result.target.department == "Payroll & Benefits"
    assert result.target.contact == "payroll@example.com"
    assert result.target.name == "Julia Hartmann"
    assert "Routed to Payroll & Benefits" in result.reason


def test_falls_back_to_recruiter_when_router_has_no_confident_match(tmp_path):
    result = _qa_with_router(tmp_path).ask(OFFER_ID, "What's your favorite pizza topping?")

    assert isinstance(result, Handoff)
    assert result.target.department is None
    assert result.target.name == "People Operations"


def test_falls_back_to_recruiter_when_router_score_is_below_router_threshold(tmp_path):
    result = _qa_with_router(tmp_path, router_threshold=1.1).ask(OFFER_ID, "Can I expense a bike?")

    assert isinstance(result, Handoff)
    assert result.target.department is None


def test_routed_handoff_logs_the_department_on_the_miss(tmp_path):
    """Regression: department must be routed *before* logging the miss, not after
    (NOTES.md §18) — otherwise the miss row is written with no department to roll up
    by, even though the returned Handoff itself carries one."""
    qa = _qa_with_router(tmp_path)

    qa.ask(OFFER_ID, "Can I expense a bike?")

    misses = qa._miss_log.all_misses()
    assert misses[0].department == "Payroll & Benefits"


def test_unrouted_miss_is_logged_with_no_department(tmp_path):
    qa = _qa_with_router(tmp_path)

    qa.ask(OFFER_ID, "What's your favorite pizza topping?")

    misses = qa._miss_log.all_misses()
    assert misses[0].department is None


def test_falls_back_to_recruiter_when_no_router_configured(qa):
    result = qa.ask(OFFER_ID, "What's my manager's favorite coffee order?")

    assert isinstance(result, Handoff)
    assert result.target.department is None
