"""Chooses real Databricks components vs. local stubs, based on whether credentials
(and a SQL warehouse, for the Unity Catalog corpus) are configured. Centralized so the
CLI and the Streamlit app apply the same fallback instead of each guessing
independently — a teammate without credentials still gets a working (stubbed) app, no
separate code path to maintain.
"""
from __future__ import annotations

import os
from pathlib import Path

from preboard.corpus import ChunkSource, LocalMarkdownSource
from preboard.generation import Generator, StubGenerator
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever, Retriever
from preboard.routing import DirectorySource, Router, ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD

FM_ENDPOINT_ENV = "DATABRICKS_FM_ENDPOINT"
DEFAULT_FM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"
WAREHOUSE_ID_ENV = "DATABRICKS_WAREHOUSE_ID"


def has_databricks_credentials() -> bool:
    """True for either local dev (DATABRICKS_HOST + a personal access token via
    DATABRICKS_TOKEN) or a deployed Databricks App's own runtime identity (DATABRICKS_HOST
    + the OAuth client id/secret Databricks injects automatically — never DATABRICKS_TOKEN).
    Checking only for DATABRICKS_TOKEN silently degraded the deployed app to
    KeywordRetriever + StubGenerator; caught via a startup log line, not a test, since
    nothing in the test suite runs inside an actual deployed app's environment."""
    if not os.environ.get("DATABRICKS_HOST"):
        return False
    has_pat = bool(os.environ.get("DATABRICKS_TOKEN"))
    has_oauth = bool(os.environ.get("DATABRICKS_CLIENT_ID")) and bool(
        os.environ.get("DATABRICKS_CLIENT_SECRET")
    )
    return has_pat or has_oauth


def has_uc_warehouse() -> bool:
    return bool(os.environ.get(WAREHOUSE_ID_ENV))


def build_chunk_source(corpus_dir: Path) -> ChunkSource:
    """Unity Catalog when a warehouse is configured (NOTES.md §9's deferred item,
    resolved), else the local markdown files — independent of which retriever ends up
    scoring the chunks this source returns."""
    if has_databricks_credentials() and has_uc_warehouse():
        from preboard.uc_corpus import UnityCatalogSource

        return UnityCatalogSource(os.environ[WAREHOUSE_ID_ENV])
    return LocalMarkdownSource(corpus_dir)


def build_retriever(corpus_dir: Path) -> tuple[Retriever, float]:
    """Returns (retriever, confidence_threshold) — the threshold is a property of
    whichever scoring scheme comes back (ratio vs. cosine similarity aren't
    comparable numbers), so it travels with the retriever rather than being guessed
    by the caller."""
    source = build_chunk_source(corpus_dir)
    if has_databricks_credentials():
        from preboard.embedding_retrieval import EMBEDDING_CONFIDENCE_THRESHOLD, EmbeddingRetriever

        return EmbeddingRetriever(source), EMBEDDING_CONFIDENCE_THRESHOLD
    return KeywordRetriever(source), CONFIDENCE_THRESHOLD


def build_router(corpus_dir: Path) -> tuple[Router, float]:
    """Mirrors `build_retriever`'s credential check and reuses the same Retriever
    implementations, just pointed at `data/directory.md` instead of an offer's own
    corpus — but with its own threshold in the embedding case
    (`ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD`, not `EMBEDDING_CONFIDENCE_THRESHOLD`):
    short directory blurbs score lower than offer-packet text even for a correct
    match, so the two thresholds aren't interchangeable (NOTES.md §17)."""
    source = DirectorySource(corpus_dir)
    if has_databricks_credentials():
        from preboard.embedding_retrieval import EmbeddingRetriever

        return Router(EmbeddingRetriever(source)), ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD
    return Router(KeywordRetriever(source)), CONFIDENCE_THRESHOLD


def build_generator() -> Generator:
    if has_databricks_credentials():
        from preboard.generation import DatabricksFMGenerator

        endpoint_name = os.environ.get(FM_ENDPOINT_ENV, DEFAULT_FM_ENDPOINT)
        return DatabricksFMGenerator(endpoint_name)
    return StubGenerator()
