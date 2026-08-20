"""Gap report: miss log ranked by frequency, aggregated across all candidates.

NOTES.md §2: a signed cohort is often one to three people, so ranking within a cohort
is near-empty and effectively re-identifies who asked what. This always aggregates
across every offer_id in the log — there is no per-cohort view.

Grouping is by normalized exact-text match (case/whitespace/trailing-punctuation
insensitive), not semantic similarity — there's no embedding model wired in yet
(that's PR1d). Two different phrasings of the same question land in separate rows
until then.

`department_gap_report` (PR9/NOTES.md §18) rolls the same misses up by the routed
department (PR8) instead of by question text — a per-question count answers "what are
people asking that we don't have written down"; a per-department count answers "which
team's docs need the most work", which is the stat worth putting on stage.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from preboard.store import Miss, MissLog

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[?!.]+$")

# Label for misses with no routed department — logged before routing existed (PR8),
# or the router had no confident match (NOTES.md §17's fallback-to-recruiter case).
UNROUTED_LABEL = "Unrouted"


def _normalize(question: str) -> str:
    q = question.strip().lower()
    q = _TRAILING_PUNCT_RE.sub("", q)
    return _WHITESPACE_RE.sub(" ", q)


def _most_common_department(misses: list[Miss]) -> str | None:
    departments = [m.department for m in misses if m.department is not None]
    if not departments:
        return None
    return Counter(departments).most_common(1)[0][0]


@dataclass(frozen=True)
class GapEntry:
    normalized_question: str
    example_question: str
    count: int
    distinct_offers: int
    last_seen: str
    department: str | None


def gap_report(miss_log: MissLog, top_n: int = 10) -> list[GapEntry]:
    groups: dict[str, list[Miss]] = {}
    for miss in miss_log.all_misses():
        groups.setdefault(_normalize(miss.question), []).append(miss)

    entries = [
        GapEntry(
            normalized_question=key,
            example_question=misses[-1].question,
            count=len(misses),
            distinct_offers=len({m.offer_id for m in misses}),
            last_seen=max(m.logged_at for m in misses),
            department=_most_common_department(misses),
        )
        for key, misses in groups.items()
    ]
    entries.sort(key=lambda e: (e.count, e.last_seen), reverse=True)
    return entries[:top_n]


@dataclass(frozen=True)
class DepartmentGapEntry:
    department: str
    count: int
    distinct_questions: int
    distinct_offers: int
    last_seen: str


def department_gap_report(miss_log: MissLog) -> list[DepartmentGapEntry]:
    groups: dict[str, list[Miss]] = {}
    for miss in miss_log.all_misses():
        groups.setdefault(miss.department or UNROUTED_LABEL, []).append(miss)

    entries = [
        DepartmentGapEntry(
            department=department,
            count=len(misses),
            distinct_questions=len({_normalize(m.question) for m in misses}),
            distinct_offers=len({m.offer_id for m in misses}),
            last_seen=max(m.logged_at for m in misses),
        )
        for department, misses in groups.items()
    ]
    entries.sort(key=lambda e: e.count, reverse=True)
    return entries


def main() -> None:
    import argparse
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="preboard gap report")
    parser.add_argument("--db", type=Path, default=repo_root / "misses.db")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    miss_log = MissLog(args.db)
    entries = gap_report(miss_log, top_n=args.top)
    if not entries:
        print("No misses logged yet.")
        return

    print(f"{'#':>3}  {'count':>5}  {'offers':>6}  {'department':<22}  {'last seen':<25}  question")
    for i, e in enumerate(entries, start=1):
        dept = e.department or "-"
        print(f"{i:>3}  {e.count:>5}  {e.distinct_offers:>6}  {dept:<22}  {e.last_seen:<25}  {e.example_question}")

    print("\nBy department:")
    for d in department_gap_report(miss_log):
        print(
            f"  {d.department:<22}  {d.count:>3} misses  "
            f"{d.distinct_questions:>3} distinct questions  {d.distinct_offers:>3} offers"
        )


if __name__ == "__main__":
    main()
