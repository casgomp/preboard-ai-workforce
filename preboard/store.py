"""Miss log.

PR1a stand-in for the eventual Unity Catalog SQL table (NOTES.md stack line): same
column shape, backed by local SQLite so the loop runs without any Databricks
connection. Swapping the backend later is a new class behind the same two methods.

`department` (PR9/NOTES.md §18) records which team `QA._route` handed a miss off to,
so `gap_report.py` can roll misses up by department, not just by question text. New
column, nullable — added via `ALTER TABLE` after `CREATE TABLE IF NOT EXISTS` so an
existing `misses.db` from before this column existed still opens without migrating by
hand; `CREATE TABLE IF NOT EXISTS` alone wouldn't add a column to an already-existing
table.
"""
from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS misses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    offer_id TEXT NOT NULL,
    question TEXT NOT NULL,
    top_score REAL NOT NULL,
    logged_at TEXT NOT NULL,
    department TEXT
)
"""


@dataclass(frozen=True)
class Miss:
    offer_id: str
    question: str
    top_score: float
    logged_at: str
    department: str | None


class MissLog:
    """Not just single-connection: Streamlit reruns the script per interaction, and a
    rerun can land on a different thread than the one that created a cached MissLog
    (sqlite3 connections are thread-affine by default). `check_same_thread=False` plus
    a lock trades strict thread-affinity for safe sequential access instead — fine for
    this app's write volume."""

    def __init__(self, db_path: Path | str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        with self._lock:
            self._conn.execute(_SCHEMA)
            try:
                self._conn.execute("ALTER TABLE misses ADD COLUMN department TEXT")
            except sqlite3.OperationalError:
                pass  # already has it — either CREATE TABLE just added it, or a prior run did
            self._conn.commit()

    def log_miss(
        self, offer_id: str, question: str, top_score: float, department: str | None = None
    ) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO misses (offer_id, question, top_score, logged_at, department) "
                "VALUES (?, ?, ?, ?, ?)",
                (offer_id, question, top_score, datetime.now(timezone.utc).isoformat(), department),
            )
            self._conn.commit()

    def all_misses(self) -> list[Miss]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT offer_id, question, top_score, logged_at, department FROM misses ORDER BY id"
            ).fetchall()
        return [Miss(*row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class UnityCatalogMissLog:
    """Miss log backed by Unity Catalog's `question_misses` table (PR12/NOTES.md
    §19) — same `log_miss`/`all_misses` shape as `MissLog`, so `QA` doesn't know or
    care which backend it's writing to. Used by `server.py`; the CLI/`app.py`
    fallback path keeps local SQLite (`MissLog`) — `misses.db` dying on redeploy was
    already an accepted, documented limitation there (NOTES.md §2), not something
    this PR needed to fix to converge the schema.
    """

    def __init__(self, warehouse_id: str):
        from databricks.sdk import WorkspaceClient  # noqa: PLC0415

        from preboard.uc_corpus import catalog_and_schema  # noqa: PLC0415

        catalog, schema = catalog_and_schema()
        self._warehouse_id = warehouse_id
        self._table = f"{catalog}.{schema}.question_misses"
        self._client = WorkspaceClient()

    def log_miss(
        self, offer_id: str, question: str, top_score: float, department: str | None = None
    ) -> None:
        import uuid  # noqa: PLC0415

        from databricks.sdk.service.sql import StatementParameterListItem  # noqa: PLC0415

        self._client.statement_execution.execute_statement(
            statement=(
                f"INSERT INTO {self._table} "
                "(miss_id, employee_id, question, top_score, department, logged_at) "
                "VALUES (:miss_id, :employee_id, :question, :top_score, :department, "
                "current_timestamp())"
            ),
            warehouse_id=self._warehouse_id,
            parameters=[
                StatementParameterListItem(name="miss_id", value=str(uuid.uuid4()), type="STRING"),
                StatementParameterListItem(name="employee_id", value=offer_id, type="STRING"),
                StatementParameterListItem(name="question", value=question, type="STRING"),
                StatementParameterListItem(name="top_score", value=str(top_score), type="DOUBLE"),
                StatementParameterListItem(name="department", value=department, type="STRING"),
            ],
            wait_timeout="30s",
        )

    def all_misses(self) -> list[Miss]:
        response = self._client.statement_execution.execute_statement(
            statement=(
                "SELECT employee_id, question, top_score, logged_at, department "
                f"FROM {self._table} ORDER BY logged_at"
            ),
            warehouse_id=self._warehouse_id,
            wait_timeout="30s",
        )
        rows = response.result.data_array if response.result else None
        if not rows:
            return []
        return [Miss(*row) for row in rows]
