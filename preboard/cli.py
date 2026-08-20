"""Minimal CLI front end. Databricks App UI is PR1b — deferred out of the critical path
so the framework decision doesn't block proving the loop."""
from __future__ import annotations

import argparse
from pathlib import Path

from preboard.generation import StubGenerator
from preboard.qa import Answer, Handoff
from preboard.retrieval import KeywordRetriever
from preboard.store import MissLog

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="preboard Q&A — PR1a CLI")
    parser.add_argument("--offer-id", default="jordan-rivera")
    parser.add_argument(
        "--corpus-dir", type=Path, default=REPO_ROOT / "data", help="Directory of <offer-id>.md files"
    )
    parser.add_argument(
        "--db", type=Path, default=REPO_ROOT / "misses.db", help="SQLite path for the miss log"
    )
    args = parser.parse_args()

    from preboard.qa import QA  # local import keeps module import order obvious

    qa = QA(
        retriever=KeywordRetriever(args.corpus_dir),
        generator=StubGenerator(),
        miss_log=MissLog(args.db),
    )

    print(f"preboard Q&A — offer '{args.offer_id}'. Ctrl-D to quit.")
    while True:
        try:
            question = input("\n> ").strip()
        except EOFError:
            print()
            break
        if not question:
            continue

        result = qa.ask(args.offer_id, question)
        if isinstance(result, Answer):
            print(f"{result.text}\n\n(source: {result.source_doc} — {result.source_section})")
        elif isinstance(result, Handoff):
            print(f"I'm not confident enough to answer that from the offer packet.")
            print(f"Reaching out to {result.target.name} ({result.target.contact}) on your behalf.")


if __name__ == "__main__":
    main()
