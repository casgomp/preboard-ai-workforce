"""Chooses real Databricks components vs. local stubs, based on whether credentials
(and a SQL warehouse, for the Unity Catalog corpus) are configured. Centralized so the
CLI, the Streamlit app, and server.py apply the same fallback instead of each guessing
independently — a teammate without credentials still gets a working (stubbed) app, no
separate code path to maintain.
"""
from __future__ import annotations

import os
from pathlib import Path

from preboard.corpus import ChunkSource, LocalMarkdownSource
from preboard.generation import Generator, StubGenerator
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever, Retriever
from preboard.routing import Router, ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD, UnityCatalogDirectorySource

FM_ENDPOINT_ENV = "DATABRICKS_FM_ENDPOINT"
DEFAULT_FM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


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


def resolve_warehouse_id() -> str | None:
    """PR12/NOTES.md §19, D6: DATABRICKS_HTTP_PATH (the frontend's name, e.g.
    "/sql/1.0/warehouses/<id>") and DATABRICKS_WAREHOUSE_ID (Python's original name,
    a bare id) name the same warehouse. The frontend's name wins when both exist;
    WAREHOUSE_ID still works directly so existing local .env files don't break."""
    explicit = os.environ.get("DATABRICKS_WAREHOUSE_ID")
    if explicit:
        return explicit
    http_path = os.environ.get("DATABRICKS_HTTP_PATH")
    return http_path.rstrip("/").split("/")[-1] if http_path else None


def has_uc_warehouse() -> bool:
    return bool(resolve_warehouse_id())


def build_chunk_source(corpus_dir: Path) -> ChunkSource:
    """Unity Catalog when a warehouse is configured (NOTES.md §9's deferred item,
    resolved), else the local markdown files — independent of which retriever ends up
    scoring the chunks this source returns."""
    if has_databricks_credentials() and has_uc_warehouse():
        from preboard.uc_corpus import UnityCatalogSource

        return UnityCatalogSource(resolve_warehouse_id())
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


def build_router(corpus_dir: Path) -> tuple[Router | None, float]:
    """Unlike `build_retriever`, there is no local fallback (PR12/NOTES.md §19, D4):
    `data/directory.md` is gone, and `department_contacts` in Unity Catalog is the
    only source of routing truth now — that's what lets HR edit routing with an
    `INSERT`, no redeploy. Without credentials+warehouse, routing is simply
    unavailable: `QA._route` already treats `router=None` as "fall back to the
    generic recruiter" (NOTES.md §17), so callers don't need a special case.
    `corpus_dir` is accepted only to keep this call-compatible with
    `build_retriever`'s signature at call sites; it's unused."""
    del corpus_dir
    if not (has_databricks_credentials() and has_uc_warehouse()):
        return None, 0.0

    from preboard.embedding_retrieval import EmbeddingRetriever

    source = UnityCatalogDirectorySource(resolve_warehouse_id(), *_catalog_and_schema())
    return Router(EmbeddingRetriever(source)), ROUTER_EMBEDDING_CONFIDENCE_THRESHOLD


def _catalog_and_schema() -> tuple[str, str]:
    from preboard.uc_corpus import catalog_and_schema

    return catalog_and_schema()


def build_miss_log(local_db_path: Path):
    """`UnityCatalogMissLog` (question_misses) when credentials+warehouse are
    configured, else local SQLite at `local_db_path` — mirrors `build_retriever`'s
    fallback shape. Used by `server.py`; `app.py`/`cli.py` keep local SQLite
    unconditionally (NOTES.md §2's already-accepted limitation), so this isn't
    wired into them."""
    if has_databricks_credentials() and has_uc_warehouse():
        from preboard.store import UnityCatalogMissLog

        return UnityCatalogMissLog(resolve_warehouse_id())
    from preboard.store import MissLog

    return MissLog(local_db_path)


def build_generator() -> Generator:
    if has_databricks_credentials():
        from preboard.generation import DatabricksFMGenerator

        endpoint_name = os.environ.get(FM_ENDPOINT_ENV, DEFAULT_FM_ENDPOINT)
        return DatabricksFMGenerator(endpoint_name)
    return StubGenerator()
