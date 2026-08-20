from pathlib import Path

import pytest

from preboard.document_library import DocumentLibrary, extract_text


@pytest.fixture
def library(tmp_path: Path) -> DocumentLibrary:
    return DocumentLibrary(tmp_path / "documents.db", tmp_path / "uploads")


def test_candidate_answer_is_extractive_and_cited(library):
    result = library.answer("Where can I park?", include_hr=False)

    assert result["status"] == "SUPPORTED"
    assert "Visitor parking is beside the North Lobby" in result["answer"]
    assert result["citations"][0]["title"] == "Wolfsburg First-Day Guide"


def test_candidate_cannot_retrieve_hr_only_answer(library):
    question = "What is the approved response to a delayed laptop?"

    assert library.answer(question, include_hr=False)["status"] == "NEEDS_HUMAN"
    assert library.answer(question, include_hr=True)["status"] == "SUPPORTED"


def test_unsupported_question_routes_to_owner(library):
    result = library.answer("What food is in the cafeteria today?", include_hr=False)

    assert result["status"] == "NEEDS_HUMAN"
    assert result["citations"] == []
    assert result["handoff"]["department"] == "Facilities"


def test_uploaded_text_becomes_searchable(library):
    document = library.add_document(
        filename="berlin.txt",
        content_type="text/plain",
        payload=b"Employees arriving in Berlin should use the east reception desk for badge collection.",
        title="Berlin Arrival Guide",
        department="Facilities",
        owner_name="Laura Stein",
        owner_email="facilities@example.com",
        audience="ALL_EMPLOYEES",
        uploaded_by="hr@example.com",
    )

    assert document["chunkCount"] == 1
    result = library.answer("Where is Berlin badge collection?", include_hr=False)
    assert result["status"] == "SUPPORTED"
    assert result["citations"][0]["title"] == "Berlin Arrival Guide"


def test_markdown_headings_are_not_returned_as_answer_sentences(library):
    library.add_document(
        filename="tools.md",
        content_type="text/markdown",
        payload=b"# Communication tools\n\nWe use Slack for daily communication and Google Workspace for email and calendars.",
        title="Company Tools",
        department="Workplace IT",
        owner_name="Michael Braun",
        owner_email="it@example.com",
        audience="ALL_EMPLOYEES",
        uploaded_by="hr@example.com",
    )

    result = library.answer("Which communication tools do we use?", include_hr=False)
    assert result["answer"].startswith("We use Slack")
    assert "# Communication" not in result["answer"]


def test_rejects_unsupported_files():
    with pytest.raises(ValueError, match="Supported formats"):
        extract_text("archive.zip", "application/zip", b"not a supported document format")
