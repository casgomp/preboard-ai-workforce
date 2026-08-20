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


class ChunkSource(Protocol):
    def load(self, offer_id: str) -> list[Chunk]: ...


class LocalMarkdownSource:
    """Reads `<corpus_dir>/<offer_id>.md`, one chunk per `## ` section."""

    def __init__(self, corpus_dir: Path):
        self._corpus_dir = corpus_dir

    def load(self, offer_id: str) -> list[Chunk]:
        doc_path = self._corpus_dir / f"{offer_id}.md"
        if not doc_path.exists():
            return []
        return load_chunks(doc_path)


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
