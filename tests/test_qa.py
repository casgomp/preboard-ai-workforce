from pathlib import Path

import pytest

from preboard.corpus import Chunk, LocalMarkdownSource
from preboard.generation import StubGenerator
from preboard.qa import QA, Answer, Handoff
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever, RetrievedChunk
from preboard.store import MissLog

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"
OFFER_ID = "jordan-rivera"


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
    assert "September" in result.text


def test_low_confidence_hands_off_and_logs_miss(qa):
    result = qa.ask(OFFER_ID, "What's my manager's favorite coffee order?")

    assert isinstance(result, Handoff)
    assert result.target.name == "Priya Nandakumar"

    misses = qa._miss_log.all_misses()
    assert len(misses) == 1
    assert misses[0].offer_id == OFFER_ID
    assert "coffee" in misses[0].question


def test_unknown_offer_id_with_no_offer_specific_match_hands_off(qa):
    result = qa.ask("someone-else", "When does my signing bonus get paid?")

    assert isinstance(result, Handoff)
    assert result.target.name == "People Ops"


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

    def generate(self, question, chunks):
        self.received_chunks = chunks
        return "stub answer"


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
