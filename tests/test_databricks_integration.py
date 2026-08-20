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

from preboard.wiring import has_databricks_credentials, resolve_warehouse_id  # noqa: E402

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_DATABRICKS_INTEGRATION_TESTS") != "1" or not has_databricks_credentials(),
    reason="set RUN_DATABRICKS_INTEGRATION_TESTS=1 with DATABRICKS_HOST/TOKEN configured to run",
)

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"

GROUNDED_CASES = [
    ("E001", "When does my laptop arrive?"),
    ("E001", "When does my signing bonus get paid?"),
    ("E002", "Is my offer contingent on a reference check?"),
    ("E002", "When does my laptop arrive?"),
]

UNGROUNDED_CASES = [
    ("E001", "What's your favorite pizza topping?"),
    ("E002", "What's my manager's favorite coffee order?"),
    ("E001", "Can I negotiate a higher salary before I start?"),
    ("E002", "Will I get stock options?"),
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
        doc_id="E001",
        section="Compensation and signing bonus",
        text=(
            "Your signing bonus (as stated in your offer letter) pays out with your second "
            "paycheck, not your first. It is subject to a 12-month clawback if you leave "
            "voluntarily before your first anniversary."
        ),
    )

    answer = generator.generate("When does my signing bonus get paid?", [chunk])

    assert answer.strip()
    assert "second paycheck" in answer.lower() or "second pay" in answer.lower()


@pytest.mark.skipif(not resolve_warehouse_id(), reason="no warehouse configured")
class TestUnityCatalogSource:
    """Requires `preboard.uc_corpus` to have been ingested already — this tests
    reading, not re-ingesting on every run."""

    def test_reads_the_same_chunks_as_the_local_files(self):
        from preboard.corpus import LocalMarkdownSource
        from preboard.uc_corpus import UnityCatalogSource

        uc_source = UnityCatalogSource(resolve_warehouse_id())
        local_source = LocalMarkdownSource(CORPUS_DIR)

        for offer_id in ("E001", "E002"):
            uc_chunks = uc_source.load(offer_id)
            local_chunks = local_source.load(offer_id)
            assert [(c.doc_id, c.section, c.text) for c in uc_chunks] == [
                (c.doc_id, c.section, c.text) for c in local_chunks
            ]

    def test_unknown_offer_gets_only_shared_company_content(self):
        from preboard.corpus import SHARED_DOC_ID
        from preboard.uc_corpus import UnityCatalogSource

        source = UnityCatalogSource(resolve_warehouse_id())
        chunks = source.load("nonexistent-offer")

        assert chunks
        assert all(c.doc_id == SHARED_DOC_ID for c in chunks)


@pytest.mark.skipif(not resolve_warehouse_id(), reason="no warehouse configured")
class TestUnityCatalogDirectorySource:
    """Requires `frontend/databricks/setup_tables.sql` + `seed_data.sql` to have been
    run already (NOTES.md §19) — this tests reading department_contacts, not seeding
    it. Scores are printed rather than hard-asserted into a pass/fail band for most
    cases: this is the calibration record (like GROUNDED_CASES above), not a fixed
    contract, since routing.ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD was set from
    exactly this kind of probe against the *previous* directory content (§17) and
    should be re-checked, not assumed, whenever department_contacts' prose changes."""

    def _router(self):
        from preboard.embedding_retrieval import EmbeddingRetriever
        from preboard.routing import Router, UnityCatalogDirectorySource
        from preboard.uc_corpus import catalog_and_schema

        catalog, schema = catalog_and_schema()
        source = UnityCatalogDirectorySource(resolve_warehouse_id(), catalog, schema)
        return Router(EmbeddingRetriever(source))

    def test_loads_all_four_departments(self):
        from preboard.routing import UnityCatalogDirectorySource
        from preboard.uc_corpus import catalog_and_schema

        catalog, schema = catalog_and_schema()
        source = UnityCatalogDirectorySource(resolve_warehouse_id(), catalog, schema)

        sections = {c.section for c in source.load("ignored")}
        assert sections == {"Workplace IT", "Facilities", "People Operations", "Learning & Onboarding"}

    @pytest.mark.parametrize(
        "question",
        [
            "My laptop never arrived, who do I contact?",
            "Where do I get a building badge?",
            "How do I set up direct deposit?",
            "When does orientation happen?",
        ],
    )
    def test_routes_a_clear_question_somewhere_confident(self, question):
        from preboard.routing import ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD

        routed = self._router().route(question)
        assert routed is not None
        target, score = routed
        print(f"{question!r} -> {target.department} ({score:.3f})")
        assert score >= ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD


def test_embedding_batches_larger_than_the_endpoint_limit():
    """Regression: databricks-gte-large-en hangs (no error, never returns) on a single
    query() call batching ~20+ inputs — reproduced with both real chunk text and
    trivial short strings, so it's an item-count limit, not a payload-size one. Found
    when data/company.md pushed a single offer's chunk count past the threshold for
    the first time. EmbeddingRetriever._embed must split into sub-batches
    (MAX_EMBED_BATCH_SIZE); this test would hang indefinitely if that regressed."""
    from preboard.corpus import Chunk
    from preboard.embedding_retrieval import EmbeddingRetriever

    class _ManyChunksSource:
        def load(self, offer_id):
            return [Chunk(doc_id="x", section=f"s{i}", text=f"filler text {i}") for i in range(25)]

    retriever = EmbeddingRetriever(_ManyChunksSource())
    results = retriever.retrieve("offer", "filler text 3")

    assert len(results) == 25
