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
    # Document title for citations (PR12/NOTES.md §19) — the doc's `# ` H1 heading,
    # read by both `load_chunks` (local) and `UnityCatalogSource` (via the
    # `company_documents.title` it was ingested with, ultimately the same H1).
    title: str | None = None


# Company-wide info (benefits, policies, IT, etc. — not tied to any one offer) lives
# as one file per topic under this subdirectory and is included alongside every
# offer's own chunks, not instead of them.
SHARED_DIR_NAME = "company"

# Filenames under SHARED_DIR_NAME that exist for reference but aren't answerable
# content — kept out of the corpus the retriever actually sees.
EXCLUDED_SHARED_FILES = frozenset({"company.md"})


class ChunkSource(Protocol):
    def load(self, offer_id: str) -> list[Chunk]: ...


class LocalMarkdownSource:
    """Reads `<corpus_dir>/<offer_id>.md` plus every `.md` file under
    `<corpus_dir>/company/` (except EXCLUDED_SHARED_FILES), one chunk per `## `
    section."""

    def __init__(self, corpus_dir: Path):
        self._corpus_dir = corpus_dir

    def load(self, offer_id: str) -> list[Chunk]:
        chunks: list[Chunk] = []
        offer_path = self._corpus_dir / f"{offer_id}.md"
        if offer_path.exists():
            chunks.extend(load_chunks(offer_path))

        shared_dir = self._corpus_dir / SHARED_DIR_NAME
        if shared_dir.is_dir():
            for doc_path in sorted(shared_dir.glob("*.md")):
                if doc_path.name in EXCLUDED_SHARED_FILES:
                    continue
                chunks.extend(load_chunks(doc_path))
        return chunks


def load_chunks(doc_path: Path) -> list[Chunk]:
    """Split a markdown doc into one chunk per `## ` section; the first `# ` line, if
    any, becomes every chunk's citation title."""
    raw = doc_path.read_text(encoding="utf-8")
    doc_id = doc_path.stem
    chunks: list[Chunk] = []
    section = None
    buf: list[str] = []
    title: str | None = None

    def flush() -> None:
        if section is not None and buf:
            chunks.append(Chunk(doc_id=doc_id, section=section, text="\n".join(buf).strip(), title=title))

    for line in raw.splitlines():
        if line.startswith("## "):
            flush()
            section = line[3:].strip()
            buf = []
        elif line.startswith("# "):
            if title is None:
                title = line[2:].strip()
        else:
            buf.append(line)
    flush()
    return chunks
