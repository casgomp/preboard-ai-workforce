"""FastAPI service used by the React frontend.

The service is not a public identity provider. React verifies the signed application
session, then forwards the verified role and subject with a shared service key.
"""
from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

from preboard.document_library import DocumentLibrary
from preboard.gap_report import department_gap_report, gap_report
from preboard.store import MissLog

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
SERVICE_KEY = os.environ.get("PREBOARD_API_SECRET", "preboard-local-api-secret")
library = DocumentLibrary(
    Path(os.environ.get("PREBOARD_DOCUMENT_DB", ROOT / "documents.db")),
    Path(os.environ.get("PREBOARD_UPLOAD_DIR", ROOT / "uploads")),
)
miss_log = MissLog(Path(os.environ.get("PREBOARD_MISS_DB", ROOT / "misses.db")))

app = FastAPI(title="Preboard API", version="1.0.0")


class Principal(BaseModel):
    role: Literal["CANDIDATE", "HR"]
    subject: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=600)
    scope: Literal["candidate", "hr"] = "candidate"

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Type a question first.")
        return value


def principal(
    x_preboard_service_key: str = Header(default=""),
    x_preboard_role: str = Header(default=""),
    x_preboard_subject: str = Header(default=""),
) -> Principal:
    if not hmac.compare_digest(x_preboard_service_key, SERVICE_KEY):
        raise HTTPException(status_code=401, detail="Invalid internal service credentials.")
    if x_preboard_role not in {"CANDIDATE", "HR"} or not x_preboard_subject:
        raise HTTPException(status_code=401, detail="Missing verified application identity.")
    return Principal(role=x_preboard_role, subject=x_preboard_subject)


def require_hr(identity: Principal = Depends(principal)) -> Principal:
    if identity.role != "HR":
        raise HTTPException(status_code=403, detail="HR access required.")
    return identity


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/v1/questions")
def ask_question(request: QuestionRequest, identity: Principal = Depends(principal)) -> dict:
    if request.scope == "hr" and identity.role != "HR":
        raise HTTPException(status_code=403, detail="HR document access required.")
    result = library.answer(request.question.strip(), include_hr=request.scope == "hr")
    if result["status"] == "NEEDS_HUMAN":
        miss_log.log_miss(identity.subject, request.question.strip(), 0.0, department=result["handoff"]["department"])
    return result


@app.get("/v1/documents")
def documents(_: Principal = Depends(require_hr)) -> dict:
    return {"documents": library.list_documents()}


@app.post("/v1/documents", status_code=201)
async def upload_document(
    title: str = Form(...),
    department: str = Form(...),
    ownerName: str = Form(...),
    ownerEmail: str = Form(...),
    audience: Literal["ALL_EMPLOYEES", "HR_ONLY"] = Form("ALL_EMPLOYEES"),
    file: UploadFile = File(...),
    identity: Principal = Depends(require_hr),
) -> dict:
    payload = await file.read()
    if not all(value.strip() for value in (title, department, ownerName, ownerEmail)):
        raise HTTPException(status_code=400, detail="Title, department and owner contact are required.")
    try:
        document = library.add_document(filename=file.filename or "document", content_type=file.content_type or "application/octet-stream", payload=payload, title=title.strip(), department=department.strip(), owner_name=ownerName.strip(), owner_email=ownerEmail.strip(), audience=audience, uploaded_by=identity.subject)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"document": document}


@app.get("/v1/knowledge-gaps")
def knowledge_gaps(_: Principal = Depends(require_hr)) -> dict:
    return {
        "departments": [
            {
                "department": entry.department,
                "count": entry.count,
                "distinctQuestions": entry.distinct_questions,
                "distinctOffers": entry.distinct_offers,
                "lastSeen": entry.last_seen,
            }
            for entry in department_gap_report(miss_log)
        ],
        "questions": [
            {
                "question": entry.example_question,
                "department": entry.department,
                "count": entry.count,
                "distinctOffers": entry.distinct_offers,
                "lastSeen": entry.last_seen,
            }
            for entry in gap_report(miss_log)
        ],
    }
