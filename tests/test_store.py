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
