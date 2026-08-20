"""Corpus retrieval.

`KeywordRetriever` here is the PR1a stand-in for real semantic retrieval (NOTES.md
§5): chunks come from a `ChunkSource` (corpus.py — local markdown or Unity Catalog)
and are scored by token overlap with the question. `EmbeddingRetriever`
(embedding_retrieval.py) replaces the scoring with real cosine similarity over a
Databricks embeddings endpoint but shares the same `Retriever` protocol and the same
`ChunkSource` abstraction, so callers don't care which retriever or which chunk
storage backend is wired in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from preboard.corpus import Chunk, ChunkSource

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


def _overlap(q_tokens: set[str], c_tokens: set[str]) -> set[str]:
    """Exact matches, plus a prefix match for tokens of 4+ chars (PR12/NOTES.md §19,
    folded in from PLAN_PR10 D2) — ported from the frontend's `wordMatches`
    (`grounding.ts`, deleted here) so "park" still matches a chunk that only says
    "parking", and "badge" matches "badges". Short tokens are excluded from prefix
    matching because they produce too many accidental matches ("in" would prefix-match
    "info", "internal", ...)."""
    direct = q_tokens & c_tokens
    prefix = {
        qt
        for qt in q_tokens - direct
        if len(qt) >= 4 and any(len(ct) >= 4 and (ct.startswith(qt) or qt.startswith(ct)) for ct in c_tokens)
    }
    return direct | prefix


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float


class Retriever(Protocol):
    def retrieve(self, offer_id: str, question: str) -> list[RetrievedChunk]: ...


class KeywordRetriever:
    """Loads chunks from a `ChunkSource` and scores sections by token overlap."""

    def __init__(self, source: ChunkSource):
        self._source = source

    def retrieve(self, offer_id: str, question: str) -> list[RetrievedChunk]:
        chunks = self._source.load(offer_id)
        if not chunks:
            return []

        q_tokens = _tokenize(question)
        if not q_tokens:
            return []

        results = []
        for chunk in chunks:
            c_tokens = _tokenize(chunk.text) | _tokenize(chunk.section)
            if not c_tokens:
                continue
            overlap = _overlap(q_tokens, c_tokens)
            if len(overlap) < min(MIN_OVERLAP_TOKENS, len(q_tokens)):
                continue
            score = len(overlap) / len(q_tokens)
            results.append(RetrievedChunk(chunk=chunk, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        return results
