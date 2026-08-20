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


@dataclass(frozen=True)
class Answer:
    text: str
    source_doc: str
    source_section: str


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

        text = self._generator.generate(question, top.chunk)
        return Answer(
            text=text,
            source_doc=top.chunk.doc_id,
            source_section=top.chunk.section,
        )
