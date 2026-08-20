"""Local company-document library with extractive, citation-first answers.

This is the authoritative document path for the React application. It deliberately
returns source sentences instead of model-authored prose: unsupported questions are
routed to a named owner and logged by the API as knowledge gaps.
"""
from __future__ import annotations

import html
import io
import json
import re
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

DocumentAudience = Literal["ALL_EMPLOYEES", "HR_ONLY"]

MAX_FILE_BYTES = 5 * 1024 * 1024
SUPPORTED_EXTENSIONS = {"pdf", "txt", "md", "csv", "json", "html", "htm"}
_STOP_WORDS = {
    "a", "about", "an", "and", "are", "can", "day", "do", "first", "for", "from",
    "how", "i", "in", "is", "it", "me", "my", "of", "on", "or", "should", "the",
    "to", "what", "when", "where", "which", "who", "will", "with",
}
_SYNONYMS = {
    "arrive": ["arrival", "lobby", "reception"],
    "go": ["arrival", "lobby", "reception"],
    "park": ["parking"],
    "bring": ["photo", "identification"],
    "wear": ["clothing", "attire", "casual"],
    "computer": ["laptop", "device"],
    "pay": ["payroll"],
}
_CONTACTS = [
    {"department": "Workplace IT", "person": "Michael Braun", "email": "workplace-it@dayone.demo", "terms": ["account", "computer", "device", "email", "it", "laptop", "login", "software", "technical"]},
    {"department": "Facilities", "person": "Laura Stein", "email": "facilities@dayone.demo", "terms": ["access", "badge", "building", "cafeteria", "desk", "food", "office", "park", "parking", "room", "transport"]},
    {"department": "People Operations", "person": "Julia Hartmann", "email": "people-operations@dayone.demo", "terms": ["benefit", "contract", "document", "holiday", "hr", "pay", "payroll", "policy", "salary", "tax"]},
    {"department": "Learning & Onboarding", "person": "Felix Weber", "email": "onboarding@dayone.demo", "terms": ["course", "learn", "orientation", "training"]},
]
_SEEDS = [
    {"id": "DOC-WOB-ARRIVAL", "title": "Wolfsburg First-Day Guide", "filename": "wolfsburg-first-day.md", "mime_type": "text/markdown", "department": "People Operations", "owner_name": "Julia Hartmann", "owner_email": "people-operations@dayone.demo", "audience": "ALL_EMPLOYEES", "text": "Your first day begins at 08:45 at the North Lobby of the Wolfsburg office. Bring a government-issued photo ID for reception. Smart casual clothing is appropriate; you do not need formal business attire. Your manager meets you at 09:00, followed by laptop setup at 09:30, team introductions at 10:30, lunch at 12:00 and orientation at 14:00. Visitor parking is beside the North Lobby, and reception can validate your visitor pass."},
    {"id": "DOC-IT-SETUP", "title": "Employee IT Setup Guide", "filename": "employee-it-setup.md", "mime_type": "text/markdown", "department": "Workplace IT", "owner_name": "Michael Braun", "owner_email": "workplace-it@dayone.demo", "audience": "ALL_EMPLOYEES", "text": "Workplace IT provides the assigned laptop during the 09:30 setup session. The employee account and multi-factor authentication are activated with an IT specialist. Required software is installed from the company software portal. Never share a password or authentication code. For device, account or software access problems, contact Workplace IT at workplace-it@dayone.demo."},
    {"id": "DOC-HR-PAPERWORK", "title": "New Starter Paperwork Guide", "filename": "starter-paperwork.md", "mime_type": "text/markdown", "department": "People Operations", "owner_name": "Julia Hartmann", "owner_email": "people-operations@dayone.demo", "audience": "ALL_EMPLOYEES", "text": "New starters must provide any requested tax identification and payroll documents through the secure employee portal before the stated deadline. Do not send identity documents by ordinary email. People Operations confirms when payroll information is complete. Questions about contracts, payroll documents or employee records should be sent to people-operations@dayone.demo."},
    {"id": "DOC-HR-OPS", "title": "HR Day One Escalation Playbook", "filename": "hr-escalation-playbook.md", "mime_type": "text/markdown", "department": "People Operations", "owner_name": "Sarah Weber", "owner_email": "sarah.weber@dayone.demo", "audience": "HR_ONLY", "text": "HR must escalate a delayed critical Day One fact when the employee starts within seven days. For a delayed laptop, the approved first response is to ask Workplace IT to reserve a temporary device. For a delayed badge, Facilities should prepare temporary building access. Every intervention must retain the source fact, accountable owner and event timestamp."},
]


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    filename: str
    mimeType: str
    department: str
    ownerName: str
    ownerEmail: str
    audience: DocumentAudience
    status: str
    createdAt: str
    chunkCount: int


def _clean_text(value: str) -> str:
    value = value.replace("\r", "")
    value = re.sub(r"[ \t]+", " ", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def extract_text(filename: str, content_type: str, payload: bytes) -> str:
    if len(payload) > MAX_FILE_BYTES:
        raise ValueError("Documents must be 5 MB or smaller for this demo.")
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Supported formats are PDF, TXT, Markdown, CSV, JSON and HTML.")
    if extension == "pdf":
        from pypdf import PdfReader

        text = "\n\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(payload)).pages)
    else:
        text = payload.decode("utf-8", errors="replace")
        if extension in {"html", "htm"} or content_type == "text/html":
            text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", " ", text, flags=re.IGNORECASE)
            text = html.unescape(re.sub(r"<[^>]+>", " ", text))
        elif extension == "json":
            try:
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                pass
    text = _clean_text(text)
    if len(text) < 40:
        raise ValueError("No usable text could be extracted from this document.")
    return text


def chunk_text(text: str, target_size: int = 900) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) > target_size:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        chunks.append(current)
    split_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= target_size * 1.7:
            split_chunks.append(chunk)
        else:
            current_sentences = ""
            for sentence in re.split(r"(?<=[.!?])\s+", chunk):
                sentence = sentence.strip()
                if current_sentences and len(current_sentences) + len(sentence) > target_size:
                    split_chunks.append(current_sentences)
                    current_sentences = sentence
                else:
                    current_sentences = f"{current_sentences} {sentence}".strip()
            if current_sentences:
                split_chunks.append(current_sentences)
    return split_chunks


def _tokenize(value: str) -> list[str]:
    raw = [token for token in re.findall(r"[a-z0-9-]+", value.lower()) if (len(token) > 2 or token == "go") and token not in _STOP_WORDS]
    expanded: list[str] = []
    for token in raw:
        expanded.extend([token, *_SYNONYMS.get(token, [])])
    return list(dict.fromkeys(expanded))


def _word_matches(words: set[str], token: str) -> bool:
    return token in words or (len(token) >= 4 and any(len(word) >= 4 and (word.startswith(token) or token.startswith(word)) for word in words))


class DocumentLibrary:
    def __init__(self, db_path: Path, upload_dir: Path):
        self._db_path = db_path
        self._upload_dir = upload_dir
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS company_documents (
                    id TEXT PRIMARY KEY, title TEXT NOT NULL, filename TEXT NOT NULL,
                    mime_type TEXT NOT NULL, department TEXT NOT NULL, owner_name TEXT NOT NULL,
                    owner_email TEXT NOT NULL, audience TEXT NOT NULL, storage_path TEXT NOT NULL,
                    extracted_text TEXT NOT NULL, status TEXT NOT NULL, uploaded_by TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL, chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL, FOREIGN KEY(document_id) REFERENCES company_documents(id)
                );
                CREATE INDEX IF NOT EXISTS idx_document_chunks_document ON document_chunks(document_id);
            """)
            count = connection.execute("SELECT COUNT(*) FROM company_documents").fetchone()[0]
            if count == 0:
                for seed in _SEEDS:
                    self._insert(connection, storage_path=f"seed://{seed['filename']}", uploaded_by="system-seed", **seed)

    def _insert(self, connection: sqlite3.Connection, *, id: str, title: str, filename: str, mime_type: str, department: str, owner_name: str, owner_email: str, audience: DocumentAudience, text: str, storage_path: str, uploaded_by: str) -> Document:
        created_at = datetime.now(timezone.utc).isoformat()
        chunks = chunk_text(text)
        connection.execute("INSERT INTO company_documents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (id, title, filename, mime_type, department, owner_name, owner_email, audience, storage_path, text, "READY", uploaded_by, created_at))
        connection.executemany("INSERT INTO document_chunks VALUES (?,?,?,?)", [(f"{id}-{index}", id, index, content) for index, content in enumerate(chunks)])
        return Document(id, title, filename, mime_type, department, owner_name, owner_email, audience, "READY", created_at, len(chunks))

    def list_documents(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("""SELECT d.id,d.title,d.filename,d.mime_type,d.department,d.owner_name,d.owner_email,d.audience,d.status,d.created_at,COUNT(c.id) AS chunk_count FROM company_documents d LEFT JOIN document_chunks c ON c.document_id=d.id GROUP BY d.id ORDER BY d.created_at DESC""").fetchall()
        return [asdict(Document(row["id"], row["title"], row["filename"], row["mime_type"], row["department"], row["owner_name"], row["owner_email"], row["audience"], row["status"], row["created_at"], row["chunk_count"])) for row in rows]

    def add_document(self, *, filename: str, content_type: str, payload: bytes, title: str, department: str, owner_name: str, owner_email: str, audience: DocumentAudience, uploaded_by: str) -> dict:
        text = extract_text(filename, content_type, payload)
        document_id = str(uuid.uuid4())
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "-", filename)
        storage_dir = self._upload_dir / document_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        storage_path = storage_dir / safe_name
        storage_path.write_bytes(payload)
        with self._connect() as connection:
            document = self._insert(connection, id=document_id, title=title, filename=filename, mime_type=content_type or "application/octet-stream", department=department, owner_name=owner_name, owner_email=owner_email, audience=audience, text=text, storage_path=str(storage_path), uploaded_by=uploaded_by)
        return asdict(document)

    def answer(self, question: str, include_hr: bool) -> dict:
        tokens = _tokenize(question)
        with self._connect() as connection:
            rows = connection.execute("""SELECT c.document_id,d.title,d.department,d.owner_name,d.owner_email,d.audience,c.content FROM document_chunks c JOIN company_documents d ON d.id=c.document_id WHERE d.status='READY' AND (? OR d.audience='ALL_EMPLOYEES')""", (include_hr,)).fetchall()
        minimum = 2 if len(tokens) >= 3 else 1
        ranked = []
        for row in rows:
            words = set(re.findall(r"[a-z0-9]+", f"{row['title']} {row['department']} {row['content']}".lower()))
            score = sum(_word_matches(words, token) for token in tokens)
            if score >= minimum:
                ranked.append((score, row))
        ranked.sort(key=lambda item: item[0], reverse=True)
        supported = []
        for _, row in ranked[:3]:
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", row["content"]):
                sentence = sentence.strip()
                if sentence.startswith("#"):
                    continue
                words = set(re.findall(r"[a-z0-9]+", sentence.lower()))
                score = sum(_word_matches(words, token) for token in tokens)
                if len(sentence) > 20 and score > 0:
                    supported.append((score, row, sentence))
        supported.sort(key=lambda item: item[0], reverse=True)
        if tokens and supported:
            sentences = list(dict.fromkeys(item[2] for item in supported))[:3]
            citations = []
            seen = set()
            for _, row, sentence in supported:
                if row["document_id"] not in seen:
                    citations.append({"documentId": row["document_id"], "title": row["title"], "excerpt": sentence})
                    seen.add(row["document_id"])
                if len(citations) == 3:
                    break
            return {"status": "SUPPORTED", "answer": " ".join(sentences), "citations": citations}
        normalized = question.lower()
        contact = max(_CONTACTS, key=lambda item: sum(term in normalized for term in item["terms"]))
        handoff = {key: contact[key] for key in ("department", "person", "email")}
        return {"status": "NEEDS_HUMAN", "answer": f"I couldn’t find a supported answer in the available company documents. Please contact {contact['department']} for a verified answer.", "citations": [], "handoff": handoff}
