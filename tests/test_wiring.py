"""Regression coverage for has_databricks_credentials(): a deployed Databricks App's
own OAuth runtime identity (DATABRICKS_CLIENT_ID/SECRET) was silently treated as "no
credentials" because the check only looked for DATABRICKS_TOKEN, degrading the
deployed app to KeywordRetriever + StubGenerator without any error or test failure
(NOTES.md §12). Caught only by adding a startup log line and reading deployed logs —
no unit test runs inside an actual deployed app's environment, so these tests can only
verify the env-var logic itself, not that Databricks really injects these var names.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from preboard.retrieval import CONFIDENCE_THRESHOLD, KeywordRetriever
from preboard.routing import Router
from preboard.wiring import build_router, has_databricks_credentials

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_CLIENT_ID", "DATABRICKS_CLIENT_SECRET"):
        monkeypatch.delenv(var, raising=False)


def test_no_host_means_no_credentials(monkeypatch):
    monkeypatch.setenv("DATABRICKS_TOKEN", "x")
    assert has_databricks_credentials() is False


def test_host_and_pat_is_local_dev(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://x")
    monkeypatch.setenv("DATABRICKS_TOKEN", "x")
    assert has_databricks_credentials() is True


def test_host_and_oauth_client_is_a_deployed_app(monkeypatch):
    """This is the case that was broken: a real deployed Databricks App."""
    monkeypatch.setenv("DATABRICKS_HOST", "https://x")
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "x")
    monkeypatch.setenv("DATABRICKS_CLIENT_SECRET", "x")
    assert has_databricks_credentials() is True


def test_host_with_only_client_id_is_not_enough(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://x")
    monkeypatch.setenv("DATABRICKS_CLIENT_ID", "x")
    assert has_databricks_credentials() is False


def test_host_alone_is_not_enough(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://x")
    assert has_databricks_credentials() is False


def test_build_router_without_credentials_mirrors_build_retriever():
    """No credentials configured (clean_env, autouse) -> keyword-scored router, same
    threshold constant KeywordRetriever-scored retrieval uses (NOTES.md §17)."""
    router, threshold = build_router(CORPUS_DIR)

    assert isinstance(router, Router)
    assert isinstance(router._retriever, KeywordRetriever)
    assert threshold == CONFIDENCE_THRESHOLD
