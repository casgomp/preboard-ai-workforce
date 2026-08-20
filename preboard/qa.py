"""Orchestration: ask -> grounded answer with citation, or handoff, with a miss logged.

Encodes NOTES.md §1: only answer/handoff/log (never rank or write to an HR system,
invariant 1); no answer without a retrieved chunk (invariant 3); low confidence hands
off to a named human (invariant 4).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from preboard.generation import Generator
from preboard.handoff import HandoffTarget, handoff_target
from preboard.offers import offer_info
from preboard.retrieval import Retriever
from preboard.routing import Router
from preboard.store import MissLog

# A broad question ("what do I need to do before I start?") can genuinely span several
# offer-packet sections; answering from only the single top-scored chunk left real
# information out (PR4). Additional chunks are included as supporting context, but
# only if they're still reasonably close to the top match — a low-relevance chunk
# tagging along would dilute the answer without adding anything grounded.
MAX_SUPPORTING_CHUNKS = 3
SUPPORTING_SCORE_RATIO = 0.6

# Guessed against the corpus's own lead-time language ("about a week", "ten days",
# "three business days before you start") — not empirically probed like
# EMBEDDING_CONFIDENCE_THRESHOLD (see NOTES.md §16/D4). Ordered by descending
# days-until-start threshold; _tminus_guidance returns the first satisfied band, so
# earlier entries must have the larger threshold.
_TMINUS_BANDS: list[tuple[int, str]] = [
    (
        60,
        "More than 8 weeks out: reassure the candidate nothing is overdue yet — most "
        "pre-start items (equipment, paperwork) haven't started their lead time.",
    ),
    (
        14,
        "2-8 weeks out: pre-start items may be in motion soon; mention timing "
        "normally, no urgency.",
    ),
    (
        4,
        "1-2 weeks out: this is close. If an excerpt states a lead time before the "
        "start date, say it should be arriving soon and worth checking on.",
    ),
]
_TMINUS_OVERDUE_GUIDANCE = (
    "3 days or fewer until start, or the start date has passed: if an excerpt gives "
    "a lead time before the start date with nothing to suggest it happened, treat it "
    "as overdue and tell the candidate to escalate now, not wait."
)


def _tminus_guidance(delta_days: int) -> str:
    for threshold, guidance in _TMINUS_BANDS:
        if delta_days >= threshold:
            return guidance
    return _TMINUS_OVERDUE_GUIDANCE


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
    so callers pass it explicitly rather than QA importing one retriever's constant.

    `router`/`router_threshold` (PR8/NOTES.md §17) are optional — `None` keeps the
    plain per-offer `handoff_target` fallback, so existing callers/tests that only
    pass the required five arguments are unaffected."""

    def __init__(
        self,
        retriever: Retriever,
        generator: Generator,
        miss_log: MissLog,
        confidence_threshold: float,
        router: Router | None = None,
        router_threshold: float = 0.0,
    ):
        self._retriever = retriever
        self._generator = generator
        self._miss_log = miss_log
        self._confidence_threshold = confidence_threshold
        self._router = router
        self._router_threshold = router_threshold

    def ask(self, offer_id: str, question: str, as_of: date | None = None) -> AnswerResult:
        """`as_of` overrides "today" for the date/T-minus context injected into the
        generated answer (PR7/NOTES.md §16, D3) — demo-only, so the same question can
        be shown at two points on the countdown without waiting real days. It affects
        only the prompt text built below; it never reaches `log_miss` or auth, so it
        carries no security weight even though it's an unauthenticated override."""
        results = self._retriever.retrieve(offer_id, question)
        top = results[0] if results else None
        top_score = top.score if top else 0.0

        if top is None or top_score < self._confidence_threshold:
            self._miss_log.log_miss(offer_id, question, top_score)
            target, reason = self._route(offer_id, question)
            return Handoff(target=target, reason=reason)

        supporting = [
            r for r in results[:MAX_SUPPORTING_CHUNKS] if r.score >= top_score * SUPPORTING_SCORE_RATIO
        ]
        chunks = [r.chunk for r in supporting]

        text = self._generator.generate(question, chunks, self._date_context(offer_id, as_of))
        return Answer(
            text=text,
            citations=[Citation(source_doc=c.doc_id, source_section=c.section) for c in chunks],
        )

    def _route(self, offer_id: str, question: str) -> tuple[HandoffTarget, str]:
        """Routes to the best-matching department (PR8/NOTES.md §17) when a router is
        configured and confident; falls back to the plain per-offer recruiter
        otherwise — same "never guess" default as invariant §1.4 applied to routing
        itself, not just answering."""
        if self._router is not None:
            routed = self._router.route(question)
            if routed is not None:
                target, score = routed
                if score >= self._router_threshold:
                    return target, f"Routed to {target.department} ({score:.2f} match)."
        return handoff_target(offer_id), "No confident match in the offer packet."

    def _date_context(self, offer_id: str, as_of: date | None = None) -> str | None:
        """Plain-language lines resolving the offer packet's start-date-relative
        phrasing into a concrete date (NOTES.md §15) and giving T-minus-banded
        guidance on how urgently to frame it (§16). None for offer_ids with no known
        start date (e.g. the shared-company-only fallback) — nothing to resolve or
        band without one."""
        info = offer_info(offer_id)
        if info is None:
            return None
        today = as_of or date.today()
        delta = (info.start_date - today).days
        if delta > 0:
            timing = f"in {delta} days"
        elif delta == 0:
            timing = "today"
        else:
            timing = f"{-delta} days ago"
        return (
            f"Today's date is {today.isoformat()}. This candidate's start date is "
            f"{info.start_date.isoformat()}, which is {timing}. {_tminus_guidance(delta)}"
        )
