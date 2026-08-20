"""Seeds `question_misses` by driving the real stack (PLAN_PR13 D1/B1).

On a fresh workspace the Knowledge gaps panel opens empty until someone has already
asked unanswerable questions in front of the judges — PLAN_PR12's B7 named this and
cut it. Rather than INSERT rows by hand (which would hand-pick departments the router
never actually produced), this calls `QA.ask` for a list of genuinely unanswerable
questions and lets the real retrieval/routing/miss-log path write them, the same way
`preboard.cli`/`server.py` would. A clean run through here is also a smoke test that
embeddings, routing and `UnityCatalogMissLog` all still work end to end.

Run: `python -m preboard.seed_misses` (needs the same credentials as `make ingest`).
Idempotent-ish, not idempotent: each run appends another ~20-30 rows to
`question_misses` — fine for a pre-demo seed, don't run it repeatedly in front of
judges expecting a stable count.
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from preboard.qa import QA, Answer, Handoff  # noqa: E402
from preboard.wiring import build_generator, build_miss_log, build_retriever, build_router  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = REPO_ROOT / "data"
DB_PATH = REPO_ROOT / "misses.db"

# One employee_id per seeded miss (seed_data.sql's E001-E005) so the panel's
# "distinct offers" count isn't just one candidate repeated. Grouped per D1: facilities,
# payroll/HR, IT, learning, and a few genuinely unroutable questions no department's
# `covers` text should match confidently.
_QUESTIONS: list[tuple[str, str]] = [
    # Facilities
    ("E001", "Is secure bike parking available for staff?"),
    ("E002", "Is there a gym in the building?"),
    ("E003", "Where's the nearest cafeteria to my desk?"),
    ("E004", "Can I book a conference room before my start date?"),
    ("E005", "What are the building's opening hours on weekends?"),
    # Payroll / People Operations
    ("E001", "How do I change my IBAN for payroll?"),
    ("E002", "When exactly is payday each month?"),
    ("E003", "What's the process to update my tax withholding?"),
    ("E004", "How do I enroll in the benefits plan?"),
    ("E005", "How do I split my paycheck across two bank accounts?"),
    # Workplace IT
    ("E001", "How do I request a second monitor for my home office setup?"),
    ("E002", "What software will already be installed on my laptop?"),
    ("E003", "Who do I email if my company account isn't set up yet?"),
    ("E004", "Can I get a technical spec sheet for the laptop model?"),
    # Learning & Onboarding
    ("E001", "Is there a buddy system for new hires in my first week?"),
    ("E002", "Is there a self-paced course I can start before day one?"),
    ("E005", "How long does orientation usually run?"),
    # Genuinely unroutable
    ("E001", "What is the wifi password at the Munich office?"),
    ("E002", "Does the company sponsor relocation visas?"),
    ("E003", "Is there a dress code for casual Fridays?"),
    ("E004", "Can I bring a pet to the office?"),
    ("E005", "What's the company's policy on remote work from another country?"),
    ("E001", "Who won the office fantasy football league last year?"),
    ("E003", "What's the guest wifi password for visitors?"),
]


def main() -> None:
    retriever, confidence_threshold = build_retriever(CORPUS_DIR)
    router, router_threshold = build_router(CORPUS_DIR)
    miss_log = build_miss_log(DB_PATH)
    qa = QA(
        retriever=retriever,
        generator=build_generator(),
        miss_log=miss_log,
        confidence_threshold=confidence_threshold,
        router=router,
        router_threshold=router_threshold,
    )

    misses = 0
    unexpected_answers: list[str] = []
    for employee_id, question in _QUESTIONS:
        result = qa.ask(employee_id, question)
        if isinstance(result, Handoff):
            misses += 1
            print(f"  miss  [{employee_id}] {question!r} -> {result.target.department or result.target.name}")
        else:
            assert isinstance(result, Answer)
            unexpected_answers.append(question)
            print(f"  ANSWERED (not a miss, no row written) [{employee_id}] {question!r}")

    print(f"\n{misses}/{len(_QUESTIONS)} questions missed and were logged to question_misses.")
    if unexpected_answers:
        print(
            f"{len(unexpected_answers)} question(s) scored above the confidence threshold and "
            "were answered instead of logged — the seed is that much shorter. Swap them for "
            "something further from the corpus if the panel looks thin."
        )


if __name__ == "__main__":
    main()
