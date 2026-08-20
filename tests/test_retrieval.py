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


def test_single_incidental_word_match_does_not_count_as_confident():
    """Regression: 'manager' alone matched alex-chen's start-date section and returned
    an unrelated answer instead of a handoff — found by manually driving the app in a
    browser while generating data for the PR2 gap report, not by unit tests."""
    retriever = KeywordRetriever(CORPUS_DIR)
    results = retriever.retrieve("alex-chen", "What's my manager's favorite coffee order?")

    assert not results


def test_candidates_only_retrieve_their_own_corpus():
    retriever = KeywordRetriever(CORPUS_DIR)

    jordan_results = retriever.retrieve("jordan-rivera", "Is this role remote or in office?")
    alex_results = retriever.retrieve("alex-chen", "Is this role remote or in office?")

    assert jordan_results[0].chunk.doc_id == "jordan-rivera"
    assert "Austin office" in jordan_results[0].chunk.text
    assert alex_results[0].chunk.doc_id == "alex-chen"
    assert "fully remote" in alex_results[0].chunk.text
