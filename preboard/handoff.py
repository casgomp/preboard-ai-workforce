"""Fallback human to hand off to when routing (routing.py) has no confident
department match.

PR1a shipped one recruiter per hardcoded offer. PR12/NOTES.md §19 deleted that stub
map: department_contacts in Unity Catalog is now the single source of routing truth
(routing.UnityCatalogDirectorySource), and the old per-offer recruiters had no
correspondence to the converged employee set (E001-E005) anyway. What's left here is
just the generic default — same shape as People Operations' own department_contacts
row, kept as a plain constant so a handoff never has *nothing* to return, even if UC
is unreachable or the router abstains.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HandoffTarget:
    name: str
    contact: str
    department: str | None = None


_DEFAULT_TARGET = HandoffTarget(name="People Operations", contact="people-operations@dayone.demo")


def handoff_target(offer_id: str) -> HandoffTarget:
    """`offer_id` is unused — kept so call sites (qa.py) don't need a special case
    when the router itself has nothing. A real per-offer lookup was never needed
    once department_contacts became the actual routing source of truth."""
    return _DEFAULT_TARGET
