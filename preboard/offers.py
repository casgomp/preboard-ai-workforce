"""Structured offer metadata that isn't derivable from packet prose (NOTES.md §15).

The offer packet talks about start-date-relative timing ("about a week before your
start date", "by the Wednesday before") but nothing in the retrieval/generation
pipeline previously knew what today's date was or when the candidate actually starts,
so those phrases came back unresolved. This is a stub lookup, same shape as
handoff.py's per-offer target map — a real version reads this from whatever system
issues offers.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class OfferInfo:
    start_date: date


_STUB_OFFERS = {
    "jordan-rivera": OfferInfo(start_date=date(2026, 9, 14)),
    "alex-chen": OfferInfo(start_date=date(2026, 10, 5)),
}


def offer_info(offer_id: str) -> OfferInfo | None:
    return _STUB_OFFERS.get(offer_id)
