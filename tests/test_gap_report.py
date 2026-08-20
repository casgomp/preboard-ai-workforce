from preboard.gap_report import gap_report
from preboard.store import MissLog


def _seed(log: MissLog, offer_id: str, question: str, top_score: float = 0.0):
    log.log_miss(offer_id, question, top_score)


def test_groups_near_duplicate_phrasing_by_normalized_text(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "What's my manager's name?")
    _seed(log, "alex-chen", "what's my manager's name?")
    _seed(log, "alex-chen", "  What's my manager's name?!  ")

    entries = gap_report(log)

    assert len(entries) == 1
    assert entries[0].count == 3
    assert entries[0].distinct_offers == 2


def test_different_questions_stay_separate(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "What's my manager's name?")
    _seed(log, "jordan-rivera", "Is dental coverage retroactive?")

    entries = gap_report(log)

    assert len(entries) == 2


def test_ranked_by_count_descending(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "rare question")
    _seed(log, "jordan-rivera", "common question")
    _seed(log, "alex-chen", "common question")
    _seed(log, "alex-chen", "common question")

    entries = gap_report(log)

    assert entries[0].example_question == "common question"
    assert entries[0].count == 3
    assert entries[1].example_question == "rare question"


def test_top_n_limits_results(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    for i in range(5):
        _seed(log, "jordan-rivera", f"question {i}")

    entries = gap_report(log, top_n=2)

    assert len(entries) == 2


def test_empty_log_returns_empty_report(tmp_path):
    log = MissLog(tmp_path / "misses.db")

    assert gap_report(log) == []
