"""Orchestration: ask -> grounded answer with citation, or handoff, with a miss logged.

Encodes NOTES.md §1: only answer/handoff/log (never rank or write to an HR system,
invariant 1); no answer without a retrieved chunk (invariant 3); low confidence hands
off to a named human (invariant 4).
"""
from __future__ import annotations

from dataclasses import dataclass

from preboard.generation import Generator
from preboard.handoff import HandoffTarget, handoff_target
from preboard.retrieval import Retriever
from preboard.store import MissLog

# A broad question ("what do I need to do before I start?") can genuinely span several
# offer-packet sections; answering from only the single top-scored chunk left real
# information out (PR4). Additional chunks are included as supporting context, but
# only if they're still reasonably close to the top match — a low-relevance chunk
# tagging along would dilute the answer without adding anything grounded.
MAX_SUPPORTING_CHUNKS = 3
SUPPORTING_SCORE_RATIO = 0.6


@dataclass(frozen=True)
class Citation:
    source_doc: str
    source_section: str


@dataclass(frozen=True)
class Answer:
    text: str
    citations: list[Citation]


@dataclass(frozen=True)
class Handoff:
    target: HandoffTarget
    reason: str


AnswerResult = Answer | Handoff


class QA:
    """`confidence_threshold` is a property of whichever retriever's scoring scheme is
    wired in (keyword-overlap ratio vs. cosine similarity aren't comparable numbers),
    so callers pass it explicitly rather than QA importing one retriever's constant."""

    def __init__(
        self, retriever: Retriever, generator: Generator, miss_log: MissLog, confidence_threshold: float
    ):
        self._retriever = retriever
        self._generator = generator
        self._miss_log = miss_log
        self._confidence_threshold = confidence_threshold

    def ask(self, offer_id: str, question: str) -> AnswerResult:
        results = self._retriever.retrieve(offer_id, question)
        top = results[0] if results else None
        top_score = top.score if top else 0.0

        if top is None or top_score < self._confidence_threshold:
            self._miss_log.log_miss(offer_id, question, top_score)
            return Handoff(
                target=handoff_target(offer_id),
                reason="No confident match in the offer packet.",
            )

        supporting = [
            r for r in results[:MAX_SUPPORTING_CHUNKS] if r.score >= top_score * SUPPORTING_SCORE_RATIO
        ]
        chunks = [r.chunk for r in supporting]

        text = self._generator.generate(question, chunks)
        return Answer(
            text=text,
            citations=[Citation(source_doc=c.doc_id, source_section=c.section) for c in chunks],
        )
