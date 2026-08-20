from pathlib import Path

import pytest

from preboard.generation import StubGenerator
from preboard.qa import QA, Answer, Handoff
from preboard.retrieval import KeywordRetriever
from preboard.store import MissLog

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"
OFFER_ID = "jordan-rivera"


@pytest.fixture
def qa(tmp_path):
    return QA(
        retriever=KeywordRetriever(CORPUS_DIR),
        generator=StubGenerator(),
        miss_log=MissLog(tmp_path / "misses.db"),
    )


def test_grounded_answer_names_its_source(qa):
    result = qa.ask(OFFER_ID, "When is my start date?")

    assert isinstance(result, Answer)
    assert result.source_doc == OFFER_ID
    assert result.source_section == "Start date and first day"
    assert "September" in result.text


def test_low_confidence_hands_off_and_logs_miss(qa):
    result = qa.ask(OFFER_ID, "What's my manager's favorite coffee order?")

    assert isinstance(result, Handoff)
    assert result.target.name == "Priya Nandakumar"

    misses = qa._miss_log.all_misses()
    assert len(misses) == 1
    assert misses[0].offer_id == OFFER_ID
    assert "coffee" in misses[0].question


def test_unknown_offer_id_hands_off_without_crashing(qa):
    result = qa.ask("someone-else", "When do I start?")

    assert isinstance(result, Handoff)
    assert result.target.name == "People Ops"
