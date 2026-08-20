"""Routes a low-confidence handoff to the department whose directory entry best
matches the question, instead of always the same one recruiter per offer
(PR8/NOTES.md §17).

`DirectorySource` is shaped like `ChunkSource` (`load(offer_id)`) but ignores the
argument — the directory is one global document, not per-offer — which lets `Router`
reuse `KeywordRetriever`/`EmbeddingRetriever` unmodified instead of a second scoring
implementation. The retriever passed in determines the confidence semantics (token
overlap vs. cosine similarity), exactly like `QA`'s own `confidence_threshold`.
"""
from __future__ import annotations

import re
from pathlib import Path

from preboard.corpus import Chunk, load_chunks
from preboard.handoff import HandoffTarget
from preboard.retrieval import Retriever

DIRECTORY_DOC_ID = "directory"

# Directory entries are short, generic department blurbs, not detailed narrative
# offer-packet text — cosine similarity against them runs meaningfully lower than
# EMBEDDING_CONFIDENCE_THRESHOLD's calibration sample even for a *correct* top-1
# match. Probed against the real endpoint (NOTES.md §17): 5 questions that should
# route scored 0.470-0.637; 3 genuinely unrelated ones scored 0.445-0.501 — the
# ranges overlap, so no threshold separates both perfectly, same structural
# limitation as §13's broad-question case. The call here is the opposite of §13's,
# though: a wrong grounded *answer* is invariant §1.4's real failure mode (the
# candidate believes something false), but a wrong *department* is low-cost — a
# human reroutes it — so this threshold is set to route more often rather than
# default to the generic recruiter, unlike the offer-answer threshold's
# never-guess bias.
ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD = 0.45

_CONTACT_RE = re.compile(r"Contact:\s*(\S+)")


class DirectorySource:
    def __init__(self, corpus_dir: Path):
        self._path = corpus_dir / f"{DIRECTORY_DOC_ID}.md"

    def load(self, offer_id: str) -> list[Chunk]:  # offer_id ignored — one global directory
        return load_chunks(self._path) if self._path.exists() else []


def _target_from_chunk(chunk: Chunk) -> HandoffTarget:
    match = _CONTACT_RE.search(chunk.text)
    contact = match.group(1) if match else "people-ops@example.com"
    return HandoffTarget(name=chunk.section, contact=contact, department=chunk.section)


class Router:
    _DIRECTORY_KEY = "directory"  # cache key only — DirectorySource ignores it

    def __init__(self, retriever: Retriever):
        self._retriever = retriever

    def route(self, question: str) -> tuple[HandoffTarget, float] | None:
        results = self._retriever.retrieve(self._DIRECTORY_KEY, question)
        if not results:
            return None
        top = results[0]
        return _target_from_chunk(top.chunk), top.score
