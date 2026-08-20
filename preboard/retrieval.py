"""Corpus retrieval.

`KeywordRetriever` here is the PR1a stand-in for real semantic retrieval (NOTES.md
§5): chunks are loaded from a local directory per offer and scored by token overlap
with the question. `EmbeddingRetriever` (embedding_retrieval.py) replaces the scoring
with real cosine similarity over a Databricks embeddings endpoint but shares the same
`Retriever` protocol, so callers don't care which is wired in. The `offer_id` scoping
stays in the interface either way, so swapping doesn't touch callers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from preboard.corpus import Chunk, load_chunks

# Tuned by hand against data/*.md. This is a placeholder that happens to separate the
# sample corpus's in-scope and out-of-scope questions for KeywordRetriever — token
# overlap has no calibrated notion of "confident". EmbeddingRetriever uses its own
# threshold (embedding_retrieval.py), tuned against real cosine similarity scores.
CONFIDENCE_THRESHOLD = 0.2

# A single incidental shared word (e.g. "manager") was enough to clear the ratio
# threshold on an otherwise unrelated question and return a wrong answer instead of a
# handoff. Requiring at least two overlapping content words cuts that off cheaply,
# without pretending this scorer is a substitute for real semantic retrieval.
MIN_OVERLAP_TOKENS = 2

_STOPWORDS = {
    "a", "an", "the", "is", "are", "do", "does", "i", "my", "me", "to", "for", "of",
    "on", "in", "at", "and", "or", "will", "when", "what", "how", "can", "it", "be",
    "you", "your", "yours", "s", "t", "get", "have", "has", "there", "any", "about",
}

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS}


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


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
        for chunk in load_chunks(doc_path):
            c_tokens = _tokenize(chunk.text) | _tokenize(chunk.section)
            if not c_tokens:
                continue
            overlap = q_tokens & c_tokens
            if len(overlap) < min(MIN_OVERLAP_TOKENS, len(q_tokens)):
                continue
            score = len(overlap) / len(q_tokens)
            results.append(RetrievedChunk(chunk=chunk, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results
