"""Minimal CLI front end. Databricks App UI is PR1c — deferred out of the critical path
so the framework decision doesn't block proving the loop.

Auth mirrors what a real link-based front end would do: the candidate supplies a
token (`--token`), never an offer id directly. `--offer-id` is a dev bypass for local
iteration and prints a loud warning so it's never mistaken for the real flow.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from preboard.auth import InvalidToken, issue_token, verify_token
from preboard.generation import StubGenerator
from preboard.qa import QA, Answer, Handoff
from preboard.retrieval import KeywordRetriever
from preboard.store import MissLog

REPO_ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser(description="preboard Q&A — CLI")
    parser.add_argument("--token", help="Magic-link token identifying the candidate's offer")
    parser.add_argument("--offer-id", help="DEV ONLY: bypass auth and use this offer id directly")
    parser.add_argument("--issue-token", metavar="OFFER_ID", help="Mint a token for OFFER_ID and exit")
    parser.add_argument(
        "--corpus-dir", type=Path, default=REPO_ROOT / "data", help="Directory of <offer-id>.md files"
    )
    parser.add_argument(
        "--db", type=Path, default=REPO_ROOT / "misses.db", help="SQLite path for the miss log"
    )
    args = parser.parse_args()

    if args.issue_token:
        print(issue_token(args.issue_token))
        return

    if args.token:
        try:
            offer_id = verify_token(args.token)
        except InvalidToken as exc:
            print(f"Invalid or expired link: {exc}", file=sys.stderr)
            raise SystemExit(1)
    elif args.offer_id:
        print(f"[dev bypass] skipping auth, using offer '{args.offer_id}' directly", file=sys.stderr)
        offer_id = args.offer_id
    else:
        parser.error("one of --token or --offer-id is required")

    qa = QA(
        retriever=KeywordRetriever(args.corpus_dir),
        generator=StubGenerator(),
        miss_log=MissLog(args.db),
    )

    print(f"preboard Q&A — offer '{offer_id}'. Ctrl-D to quit.")
    while True:
        try:
            question = input("\n> ").strip()
        except EOFError:
            print()
            break
        if not question:
            continue

        result = qa.ask(offer_id, question)
        if isinstance(result, Answer):
            print(f"{result.text}\n\n(source: {result.source_doc} — {result.source_section})")
        elif isinstance(result, Handoff):
            print("I'm not confident enough to answer that from the offer packet.")
            print(f"Reaching out to {result.target.name} ({result.target.contact}) on your behalf.")


if __name__ == "__main__":
    main()
