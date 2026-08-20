"""Unit coverage for routing.py's pure logic (PR12/NOTES.md §19). No network here —
`UnityCatalogDirectorySource` itself is exercised by the opt-in integration suite
(tests/test_databricks_integration.py), same split as UnityCatalogSource.
"""
from preboard.corpus import Chunk
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever
from preboard.routing import Router, _parse_terms, _target_from_chunk


def test_parse_terms_handles_a_native_list():
    assert _parse_terms(["bike", "expense"]) == ["bike", "expense"]


def test_parse_terms_handles_a_json_string():
    assert _parse_terms('["bike", "expense"]') == ["bike", "expense"]


def test_parse_terms_handles_a_bare_bracketed_string():
    assert _parse_terms("[bike, expense]") == ["bike", "expense"]


def test_parse_terms_handles_none_or_empty():
    assert _parse_terms(None) == []
    assert _parse_terms("") == []


def test_target_from_chunk_extracts_person_and_contact():
    chunk = Chunk(
        doc_id="directory",
        section="Payroll & Benefits",
        text="Person: Julia Hartmann\nContact: payroll@example.com\nCovers: pay and benefits\nAlso ask about: bike",
    )

    target = _target_from_chunk(chunk)

    assert target.name == "Julia Hartmann"
    assert target.contact == "payroll@example.com"
    assert target.department == "Payroll & Benefits"


def test_target_from_chunk_falls_back_when_person_is_missing():
    chunk = Chunk(doc_id="directory", section="Facilities", text="Contact: facilities@example.com")

    target = _target_from_chunk(chunk)

    assert target.name == "Facilities"
    assert target.contact == "facilities@example.com"


class _FakeDirectorySource:
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


def test_router_matches_a_question_to_the_right_department():
    router = Router(KeywordRetriever(_FakeDirectorySource()))

    routed = router.route("Can I expense a bike?")

    assert routed is not None
    target, score = routed
    assert target.department == "Payroll & Benefits"
    assert target.contact == "payroll@example.com"
    assert score >= CONFIDENCE_THRESHOLD


def test_router_matches_equipment_questions_to_it():
    router = Router(KeywordRetriever(_FakeDirectorySource()))

    routed = router.route("My laptop never arrived, who do I contact?")

    assert routed is not None
    target, _score = routed
    assert target.department == "IT & Equipment"


def test_router_returns_none_for_a_question_matching_no_department():
    router = Router(KeywordRetriever(_FakeDirectorySource()))

    assert router.route("What's your favorite pizza topping?") is None
