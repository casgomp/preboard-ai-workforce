"""Miss log.

PR1a stand-in for the eventual Unity Catalog SQL table (NOTES.md stack line): same
column shape, backed by local SQLite so the loop runs without any Databricks
connection. Swapping the backend later is a new class behind the same two methods.
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
    logged_at TEXT NOT NULL
)
"""


@dataclass(frozen=True)
class Miss:
    offer_id: str
    question: str
    top_score: float
    logged_at: str


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
            self._conn.commit()

    def log_miss(self, offer_id: str, question: str, top_score: float) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO misses (offer_id, question, top_score, logged_at) VALUES (?, ?, ?, ?)",
                (offer_id, question, top_score, datetime.now(timezone.utc).isoformat()),
            )
            self._conn.commit()

    def all_misses(self) -> list[Miss]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT offer_id, question, top_score, logged_at FROM misses ORDER BY id"
            ).fetchall()
        return [Miss(*row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()
