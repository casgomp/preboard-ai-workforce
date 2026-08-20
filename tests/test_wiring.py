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

from preboard.wiring import build_router, has_databricks_credentials, resolve_warehouse_id

CORPUS_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for var in (
        "DATABRICKS_HOST",
        "DATABRICKS_TOKEN",
        "DATABRICKS_CLIENT_ID",
        "DATABRICKS_CLIENT_SECRET",
        "DATABRICKS_WAREHOUSE_ID",
        "DATABRICKS_HTTP_PATH",
    ):
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


def test_build_router_without_credentials_returns_none():
    """PR12/NOTES.md §19, D4: routing has no local fallback anymore — `data/directory.md`
    is gone, and `department_contacts` only exists in Unity Catalog. Without
    credentials+warehouse, `build_router` returns `(None, 0.0)`; `QA._route` already
    treats `router=None` as "fall back to the generic recruiter" (NOTES.md §17)."""
    router, threshold = build_router(CORPUS_DIR)

    assert router is None
    assert threshold == 0.0


def test_build_router_with_credentials_but_no_warehouse_returns_none(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HOST", "https://x")
    monkeypatch.setenv("DATABRICKS_TOKEN", "x")

    router, threshold = build_router(CORPUS_DIR)

    assert router is None
    assert threshold == 0.0


def test_resolve_warehouse_id_prefers_explicit_id(monkeypatch):
    monkeypatch.setenv("DATABRICKS_WAREHOUSE_ID", "abc123")
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/other456")

    assert resolve_warehouse_id() == "abc123"


def test_resolve_warehouse_id_falls_back_to_http_path(monkeypatch):
    monkeypatch.setenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/other456")

    assert resolve_warehouse_id() == "other456"


def test_resolve_warehouse_id_is_none_without_either():
    assert resolve_warehouse_id() is None
