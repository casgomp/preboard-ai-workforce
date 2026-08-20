from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from preboard.document_library import DocumentLibrary
from preboard.store import MissLog


@pytest.fixture
def client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setattr(api_main, "library", DocumentLibrary(tmp_path / "documents.db", tmp_path / "uploads"))
    monkeypatch.setattr(api_main, "miss_log", MissLog(tmp_path / "misses.db"))
    return TestClient(api_main.app)


def headers(role="CANDIDATE", subject="E001"):
    return {
        "X-Preboard-Service-Key": api_main.SERVICE_KEY,
        "X-Preboard-Role": role,
        "X-Preboard-Subject": subject,
    }


def test_rejects_direct_unauthenticated_requests(client):
    response = client.post("/v1/questions", json={"question": "Where can I park?"})
    assert response.status_code == 401


def test_candidate_cannot_use_hr_scope(client):
    response = client.post("/v1/questions", headers=headers(), json={"question": "What is the HR response?", "scope": "hr"})
    assert response.status_code == 403


def test_blank_question_is_rejected(client):
    response = client.post("/v1/questions", headers=headers(), json={"question": "   "})
    assert response.status_code == 422


def test_unsupported_question_is_visible_in_hr_gap_report(client):
    asked = client.post("/v1/questions", headers=headers(), json={"question": "What food is in the cafeteria today?", "scope": "candidate"})
    gaps = client.get("/v1/knowledge-gaps", headers=headers("HR", "hr@example.com"))

    assert asked.json()["status"] == "NEEDS_HUMAN"
    assert gaps.status_code == 200
    assert gaps.json()["questions"][0]["question"] == "What food is in the cafeteria today?"
    assert gaps.json()["departments"][0]["department"] == "Facilities"


def test_candidate_cannot_list_documents(client):
    assert client.get("/v1/documents", headers=headers()).status_code == 403


def test_hr_can_upload_document(client):
    response = client.post(
        "/v1/documents",
        headers=headers("HR", "hr@example.com"),
        data={"title": "Berlin Guide", "department": "Facilities", "ownerName": "Laura Stein", "ownerEmail": "facilities@example.com", "audience": "ALL_EMPLOYEES"},
        files={"file": ("berlin.txt", b"Berlin employees collect their badge at the east reception desk on arrival.", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["document"]["title"] == "Berlin Guide"
