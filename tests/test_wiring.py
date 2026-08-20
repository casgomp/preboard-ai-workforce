"""Regression coverage for has_databricks_credentials(): a deployed Databricks App's
own OAuth runtime identity (DATABRICKS_CLIENT_ID/SECRET) was silently treated as "no
credentials" because the check only looked for DATABRICKS_TOKEN, degrading the
deployed app to KeywordRetriever + StubGenerator without any error or test failure
(NOTES.md §12). Caught only by adding a startup log line and reading deployed logs —
no unit test runs inside an actual deployed app's environment, so these tests can only
verify the env-var logic itself, not that Databricks really injects these var names.
"""
from __future__ import annotations

import pytest

from preboard.wiring import has_databricks_credentials


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
