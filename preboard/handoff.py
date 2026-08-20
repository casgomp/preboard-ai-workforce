"""Named human to hand off to on low confidence.

PR1a stub: one recruiter per hardcoded offer. Real version looks this up per-offer from
whatever system owns candidate/recruiter pairings.

`department` (PR8/NOTES.md §17) is set when `routing.Router` matched the question to a
directory entry; `None` for the plain per-offer recruiter fallback below, which isn't
department-specific.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandoffTarget:
    name: str
    contact: str
    department: str | None = None


_STUB_TARGETS = {
    "jordan-rivera": HandoffTarget(name="Priya Nandakumar", contact="priya.n@example.com"),
    "alex-chen": HandoffTarget(name="Devon Ortiz", contact="devon.o@example.com"),
}

_DEFAULT_TARGET = HandoffTarget(name="People Ops", contact="people-ops@example.com")


def handoff_target(offer_id: str) -> HandoffTarget:
    return _STUB_TARGETS.get(offer_id, _DEFAULT_TARGET)
