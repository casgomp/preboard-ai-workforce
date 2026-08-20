from pathlib import Path

from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"


def test_retrieves_relevant_section_above_threshold():
    retriever = KeywordRetriever(CORPUS_DIR)
    results = retriever.retrieve("jordan-rivera", "When does my signing bonus get paid?")

    assert results
    assert results[0].chunk.section == "Compensation and signing bonus"
    assert results[0].score >= CONFIDENCE_THRESHOLD


def test_unrelated_question_scores_below_threshold():
    retriever = KeywordRetriever(CORPUS_DIR)
    results = retriever.retrieve("jordan-rivera", "What's your favorite pizza topping?")

    assert not results or results[0].score < CONFIDENCE_THRESHOLD


def test_unknown_offer_returns_nothing():
    retriever = KeywordRetriever(CORPUS_DIR)
    results = retriever.retrieve("nonexistent-offer", "When do I start?")

    assert results == []
