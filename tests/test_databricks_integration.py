"""Integration tests against real Databricks endpoints. Opt-in only — set
RUN_DATABRICKS_INTEGRATION_TESTS=1 to run them. They hit the network and cost tokens,
so a plain `pytest` never triggers them, even when credentials happen to be configured
(e.g. in .env for the running app) — that's a separate concern from "should this
test suite spend money right now".

Also serves as the executable record of the EMBEDDING_CONFIDENCE_THRESHOLD calibration
(NOTES.md §9): if the embedding model or corpus changes enough to break this margin,
this is what should fail and prompt a re-tune, not a coincidence discovered in a demo.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

from preboard.wiring import has_databricks_credentials  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DATABRICKS_INTEGRATION_TESTS") != "1" or not has_databricks_credentials(),
    reason="set RUN_DATABRICKS_INTEGRATION_TESTS=1 with DATABRICKS_HOST/TOKEN configured to run",
)

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"

GROUNDED_CASES = [
    ("jordan-rivera", "When does my signing bonus get paid?"),
    ("jordan-rivera", "When is my start date?"),
    ("jordan-rivera", "How much PTO do I accrue?"),
    ("alex-chen", "Is this role remote or in office?"),
    ("alex-chen", "When does my laptop arrive?"),
]

UNGROUNDED_CASES = [
    ("jordan-rivera", "What's your favorite pizza topping?"),
    ("alex-chen", "What's my manager's favorite coffee order?"),
    ("jordan-rivera", "Can I negotiate a higher salary before I start?"),
    ("alex-chen", "Will I get stock options?"),
]


@pytest.fixture
def retriever():
    from preboard.corpus import LocalMarkdownSource
    from preboard.embedding_retrieval import EmbeddingRetriever

    return EmbeddingRetriever(LocalMarkdownSource(CORPUS_DIR))


@pytest.mark.parametrize("offer_id,question", GROUNDED_CASES)
def test_grounded_question_clears_threshold(retriever, offer_id, question):
    from preboard.embedding_retrieval import EMBEDDING_CONFIDENCE_THRESHOLD

    results = retriever.retrieve(offer_id, question)
    assert results
    assert results[0].score >= EMBEDDING_CONFIDENCE_THRESHOLD, (
        f"expected a confident match, got {results[0].score:.3f} for {question!r}"
    )


@pytest.mark.parametrize("offer_id,question", UNGROUNDED_CASES)
def test_ungrounded_question_stays_below_threshold(retriever, offer_id, question):
    from preboard.embedding_retrieval import EMBEDDING_CONFIDENCE_THRESHOLD

    results = retriever.retrieve(offer_id, question)
    top_score = results[0].score if results else 0.0
    assert top_score < EMBEDDING_CONFIDENCE_THRESHOLD, (
        f"expected no confident match, got {top_score:.3f} for {question!r}"
    )


def test_generator_grounds_its_answer_in_the_chunk():
    from preboard.corpus import Chunk
    from preboard.generation import DatabricksFMGenerator
    from preboard.wiring import DEFAULT_FM_ENDPOINT

    generator = DatabricksFMGenerator(os.environ.get("DATABRICKS_FM_ENDPOINT", DEFAULT_FM_ENDPOINT))
    chunk = Chunk(
        doc_id="jordan-rivera",
        section="Compensation and signing bonus",
        text=(
            "Your signing bonus (as stated in your offer letter) pays out in your second "
            "paycheck, not your first. It is subject to a 12-month clawback if you leave "
            "voluntarily before your first anniversary."
        ),
    )

    answer = generator.generate("When does my signing bonus get paid?", [chunk])

    assert answer.strip()
    assert "second paycheck" in answer.lower() or "second pay" in answer.lower()


@pytest.mark.skipif(
    not os.environ.get("DATABRICKS_WAREHOUSE_ID"), reason="DATABRICKS_WAREHOUSE_ID not configured"
)
class TestUnityCatalogSource:
    """Requires `preboard.uc_corpus` to have been ingested already (NOTES.md §9) —
    this tests reading, not re-ingesting on every run."""

    def test_reads_the_same_chunks_as_the_local_files(self):
        from preboard.corpus import LocalMarkdownSource
        from preboard.uc_corpus import UnityCatalogSource

        uc_source = UnityCatalogSource(os.environ["DATABRICKS_WAREHOUSE_ID"])
        local_source = LocalMarkdownSource(CORPUS_DIR)

        for offer_id in ("jordan-rivera", "alex-chen"):
            uc_chunks = uc_source.load(offer_id)
            local_chunks = local_source.load(offer_id)
            assert [(c.doc_id, c.section, c.text) for c in uc_chunks] == [
                (c.doc_id, c.section, c.text) for c in local_chunks
            ]

    def test_unknown_offer_returns_nothing(self):
        from preboard.uc_corpus import UnityCatalogSource

        source = UnityCatalogSource(os.environ["DATABRICKS_WAREHOUSE_ID"])
        assert source.load("nonexistent-offer") == []
