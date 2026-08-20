from pathlib import Path

from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever
from preboard.routing import DirectorySource, Router

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"


def test_directory_source_loads_one_chunk_per_department():
    chunks = DirectorySource(CORPUS_DIR).load("ignored")

    sections = {c.section for c in chunks}
    assert sections == {
        "IT & Equipment",
        "Payroll & Benefits",
        "People Ops",
        "Facilities & Workplace",
        "Security & Compliance",
    }


def test_directory_source_ignores_offer_id():
    source = DirectorySource(CORPUS_DIR)
    assert source.load("jordan-rivera") == source.load("alex-chen") == source.load("anything")


def test_router_matches_a_question_to_the_right_department():
    router = Router(KeywordRetriever(DirectorySource(CORPUS_DIR)))

    routed = router.route("Can I expense a bike?")

    assert routed is not None
    target, score = routed
    assert target.department == "Payroll & Benefits"
    assert target.contact == "payroll@example.com"
    assert score >= CONFIDENCE_THRESHOLD


def test_router_matches_equipment_questions_to_it():
    router = Router(KeywordRetriever(DirectorySource(CORPUS_DIR)))

    routed = router.route("My laptop never arrived, who do I contact?")

    assert routed is not None
    target, _score = routed
    assert target.department == "IT & Equipment"


def test_router_returns_none_for_a_question_matching_no_department():
    router = Router(KeywordRetriever(DirectorySource(CORPUS_DIR)))

    assert router.route("What's your favorite pizza topping?") is None
