"""Corpus retrieval.

PR1a stand-in for Unity Catalog + vector search (NOTES.md §5): chunks are loaded from a
local directory per offer and scored by token overlap with the question. No embeddings.
The `offer_id` scoping stays in the interface now so swapping in real vector search
later doesn't touch callers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Tuned by hand against data/offer_packet.md. Revisit once real vector search lands —
# token overlap has no calibrated notion of "confident", this is a placeholder that
# happens to separate the sample corpus's in-scope and out-of-scope questions.
CONFIDENCE_THRESHOLD = 0.2

_STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "i", "my", "me", "to", "for", "of",
    "on", "in", "at", "and", "or", "will", "when", "what", "how", "can", "it", "be",
    "you", "your", "yours", "s", "t", "get", "have", "has", "there", "any", "about",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    section: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


def _load_chunks(doc_path: Path) -> list[Chunk]:
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


class Retriever(Protocol):
    def retrieve(self, offer_id: str, question: str) -> list[RetrievedChunk]: ...


class KeywordRetriever:
    """Loads `<corpus_dir>/<offer_id>.md` and scores sections by token overlap."""

    def __init__(self, corpus_dir: Path):
        self._corpus_dir = corpus_dir

    def retrieve(self, offer_id: str, question: str) -> list[RetrievedChunk]:
        doc_path = self._corpus_dir / f"{offer_id}.md"
        if not doc_path.exists():
            return []

        q_tokens = _tokenize(question)
        if not q_tokens:
            return []

        results = []
        for chunk in _load_chunks(doc_path):
            c_tokens = _tokenize(chunk.text) | _tokenize(chunk.section)
            if not c_tokens:
                continue
            overlap = q_tokens & c_tokens
            score = len(overlap) / len(q_tokens)
            if score > 0:
                results.append(RetrievedChunk(chunk=chunk, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results
