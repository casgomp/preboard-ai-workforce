"""Chooses real Databricks components vs. local stubs, based on whether credentials
are configured. Centralized so the CLI and the Streamlit app apply the same fallback
instead of each guessing independently — a teammate without credentials still gets a
working (stubbed) app, no separate code path to maintain.
"""
from __future__ import annotations

import os
from pathlib import Path

from preboard.generation import Generator, StubGenerator
from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever, Retriever

FM_ENDPOINT_ENV = "DATABRICKS_FM_ENDPOINT"
DEFAULT_FM_ENDPOINT = "databricks-meta-llama-3-3-70b-instruct"


def has_databricks_credentials() -> bool:
    return bool(os.environ.get("DATABRICKS_HOST")) and bool(os.environ.get("DATABRICKS_TOKEN"))


def build_retriever(corpus_dir: Path) -> tuple[Retriever, float]:
    """Returns (retriever, confidence_threshold) — the threshold is a property of
    whichever scoring scheme comes back (ratio vs. cosine similarity aren't
    comparable numbers), so it travels with the retriever rather than being guessed
    by the caller."""
    if has_databricks_credentials():
        from preboard.embedding_retrieval import EMBEDDING_CONFIDENCE_THRESHOLD, EmbeddingRetriever

        return EmbeddingRetriever(corpus_dir), EMBEDDING_CONFIDENCE_THRESHOLD
    return KeywordRetriever(corpus_dir), CONFIDENCE_THRESHOLD


def build_generator() -> Generator:
    if has_databricks_credentials():
        from preboard.generation import DatabricksFMGenerator

        endpoint_name = os.environ.get(FM_ENDPOINT_ENV, DEFAULT_FM_ENDPOINT)
        return DatabricksFMGenerator(endpoint_name)
    return StubGenerator()
