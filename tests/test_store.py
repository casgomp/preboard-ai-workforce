import sqlite3
import threading

from preboard.store import MissLog


def test_log_miss_from_a_different_thread_than_the_connection_was_created_on(tmp_path):
    """Regression: Streamlit reruns handlers on varying threads, and a cached MissLog's
    sqlite3 connection is thread-affine by default. Caught via manual browser testing
    (sqlite3.ProgrammingError) — StubGenerator/pytest alone never touch a second thread."""
    log = MissLog(tmp_path / "misses.db")
    error: list[Exception] = []

    def log_from_thread():
        try:
            log.log_miss("jordan-rivera", "some question", 0.0)
        except Exception as exc:  # noqa: BLE001
            error.append(exc)

    thread = threading.Thread(target=log_from_thread)
    thread.start()
    thread.join()

    assert not error
    assert len(log.all_misses()) == 1


def test_log_miss_stores_and_returns_department(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    log.log_miss("jordan-rivera", "Can I expense a bike?", 0.3, department="Payroll & Benefits")

    assert log.all_misses()[0].department == "Payroll & Benefits"


def test_log_miss_department_defaults_to_none(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    log.log_miss("jordan-rivera", "some question", 0.0)

    assert log.all_misses()[0].department is None


def test_opens_a_database_created_before_the_department_column_existed(tmp_path):
    """Regression: MissLog must not crash against a misses.db created before PR9
    (NOTES.md §18) added the department column — the ALTER TABLE in __init__ handles
    an existing table missing it, not just a brand-new one."""
    db_path = tmp_path / "misses.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE misses (id INTEGER PRIMARY KEY AUTOINCREMENT, offer_id TEXT NOT NULL, "
        "question TEXT NOT NULL, top_score REAL NOT NULL, logged_at TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO misses (offer_id, question, top_score, logged_at) VALUES (?, ?, ?, ?)",
        ("jordan-rivera", "old question", 0.1, "2026-01-01T00:00:00+00:00"),
    )
    conn.commit()
    conn.close()

    log = MissLog(db_path)  # must not raise
    log.log_miss("alex-chen", "new question", 0.2, department="IT & Equipment")

    misses = log.all_misses()
    assert len(misses) == 2
    assert misses[0].department is None
    assert misses[1].department == "IT & Equipment"
