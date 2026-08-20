"""Gap report: miss log ranked by frequency, aggregated across all candidates.

NOTES.md §2: a signed cohort is often one to three people, so ranking within a cohort
is near-empty and effectively re-identifies who asked what. This always aggregates
across every offer_id in the log — there is no per-cohort view.

Grouping is by normalized exact-text match (case/whitespace/trailing-punctuation
insensitive), not semantic similarity — there's no embedding model wired in yet
(that's PR1d). Two different phrasings of the same question land in separate rows
until then.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from preboard.store import Miss, MissLog

_WHITESPACE_RE = re.compile(r"\s+")
_TRAILING_PUNCT_RE = re.compile(r"[?!.]+$")


def _normalize(question: str) -> str:
    q = question.strip().lower()
    q = _TRAILING_PUNCT_RE.sub("", q)
    return _WHITESPACE_RE.sub(" ", q)


@dataclass(frozen=True)
class GapEntry:
    normalized_question: str
    example_question: str
    count: int
    distinct_offers: int
    last_seen: str


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
        )
        for key, misses in groups.items()
    ]
    entries.sort(key=lambda e: (e.count, e.last_seen), reverse=True)
    return entries[:top_n]


def main() -> None:
    import argparse
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description="preboard gap report")
    parser.add_argument("--db", type=Path, default=repo_root / "misses.db")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    entries = gap_report(MissLog(args.db), top_n=args.top)
    if not entries:
        print("No misses logged yet.")
        return

    print(f"{'#':>3}  {'count':>5}  {'offers':>6}  {'last seen':<25}  question")
    for i, e in enumerate(entries, start=1):
        print(f"{i:>3}  {e.count:>5}  {e.distinct_offers:>6}  {e.last_seen:<25}  {e.example_question}")


if __name__ == "__main__":
    main()
