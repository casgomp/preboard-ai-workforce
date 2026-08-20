"""Corpus loading, shared by every retriever (keyword, embedding, ...).

Chunking is one `Chunk` per `## `-delimited markdown section — a section is the
smallest citable unit an answer can point to.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    section: str
    text: str
    # Document title for citations (PR12/NOTES.md §19) — `UnityCatalogSource` joins
    # `company_documents.title`; `LocalMarkdownSource` leaves this None and callers
    # fall back to `doc_id`, since local stub files have no separate title record.
    title: str | None = None


# Company-wide info (benefits baseline, policies, culture — not tied to any one offer)
# lives in a doc under this id and is included alongside every offer's own chunks, not
# instead of them. Not itself a real offer_id — nothing should ever auth into it.
SHARED_DOC_ID = "company"


class ChunkSource(Protocol):
    def load(self, offer_id: str) -> list[Chunk]: ...


class LocalMarkdownSource:
    """Reads `<corpus_dir>/<offer_id>.md` plus `<corpus_dir>/company.md`, one chunk
    per `## ` section."""

    def __init__(self, corpus_dir: Path):
        self._corpus_dir = corpus_dir

    def load(self, offer_id: str) -> list[Chunk]:
        doc_ids = [offer_id] if offer_id == SHARED_DOC_ID else [offer_id, SHARED_DOC_ID]
        chunks: list[Chunk] = []
        for doc_id in doc_ids:
            doc_path = self._corpus_dir / f"{doc_id}.md"
            if doc_path.exists():
                chunks.extend(load_chunks(doc_path))
        return chunks


def load_chunks(doc_path: Path) -> list[Chunk]:
    """Split a markdown offer packet into one chunk per `## ` section."""
    raw = doc_path.read_text(encoding="utf-8")
    doc_id = doc_path.stem
    chunks: list[Chunk] = []
    section = None
    buf: list[str] = []

    def flush() -> None:
        if section is not None and buf:
            chunks.append(Chunk(doc_id=doc_id, section=section, text="\n".join(buf).strip()))

    for line in raw.splitlines():
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
            buf = []
        elif line.startswith("# "):
            continue
        else:
            buf.append(line)
    flush()
    return chunks
