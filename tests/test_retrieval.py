from pathlib import Path

from preboard.corpus import LocalMarkdownSource
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCE = LocalMarkdownSource(CORPUS_DIR)


def test_retrieves_relevant_section_above_threshold():
    retriever = KeywordRetriever(SOURCE)
    results = retriever.retrieve("E001", "When does my signing bonus get paid?")

    assert results
    assert results[0].chunk.section == "Compensation and signing bonus"
    assert results[0].score >= CONFIDENCE_THRESHOLD


def test_unrelated_question_scores_below_threshold():
    retriever = KeywordRetriever(SOURCE)
    results = retriever.retrieve("E001", "What's your favorite pizza topping?")

    assert not results or results[0].score < CONFIDENCE_THRESHOLD


def test_unknown_offer_still_surfaces_shared_company_content():
    """Company-wide info (corpus.py's SHARED_DOC_ID) isn't candidate-specific, so it's
    reachable even for an offer id with no dedicated doc — unlike offer-specific
    content, which stays properly scoped (see test_candidates_only_retrieve_their_own_corpus)."""
    retriever = KeywordRetriever(SOURCE)
    results = retriever.retrieve("nonexistent-offer", "What communication tools do we use?")

    assert results
    assert results[0].chunk.doc_id == "company"


def test_unknown_offer_has_no_offer_specific_content_to_leak():
    retriever = KeywordRetriever(SOURCE)
    results = retriever.retrieve("nonexistent-offer", "When does my signing bonus get paid?")

    assert all(r.chunk.doc_id == "company" for r in results)


def test_single_incidental_word_match_does_not_count_as_confident():
    """Regression: 'manager' alone matched a start-date section and returned an
    unrelated answer instead of a handoff — found by manually driving the app in a
    browser while generating data for the PR2 gap report, not by unit tests."""
    retriever = KeywordRetriever(SOURCE)
    results = retriever.retrieve("E002", "What's my manager's favorite coffee order?")

    assert not results


def test_candidates_only_retrieve_their_own_corpus():
    retriever = KeywordRetriever(SOURCE)
    question = "Who do I ask for when I arrive at reception on my first day?"

    e001_results = retriever.retrieve("E001", question)
    e002_results = retriever.retrieve("E002", question)

    assert e001_results[0].chunk.doc_id == "E001"
    assert "Wolfsburg" in e001_results[0].chunk.text
    assert e002_results[0].chunk.doc_id == "E002"
    assert "Berlin" in e002_results[0].chunk.text
