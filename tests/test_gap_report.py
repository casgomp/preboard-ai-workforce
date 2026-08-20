from preboard.gap_report import UNROUTED_LABEL, department_gap_report, gap_report
from preboard.store import MissLog


def _seed(
    log: MissLog, offer_id: str, question: str, top_score: float = 0.0, department: str | None = None
):
    log.log_miss(offer_id, question, top_score, department=department)


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


def test_gap_entry_reports_the_most_common_department(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "Can I expense a bike?", department="Payroll & Benefits")
    _seed(log, "alex-chen", "can i expense a bike?", department="Payroll & Benefits")

    entries = gap_report(log)

    assert entries[0].department == "Payroll & Benefits"


def test_gap_entry_department_is_none_when_unrouted(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "What's your favorite pizza topping?")

    entries = gap_report(log)

    assert entries[0].department is None


def test_department_gap_report_ranks_by_miss_count(tmp_path):
    """Regression for the bike question (NOTES.md §18): a per-department rollup, not
    just a per-question one, is what shows which team's docs need the most work."""
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "Can I expense a bike?", department="Payroll & Benefits")
    _seed(log, "alex-chen", "When's payday?", department="Payroll & Benefits")
    _seed(log, "jordan-rivera", "Where's my badge?", department="Facilities & Workplace")

    entries = department_gap_report(log)

    assert entries[0].department == "Payroll & Benefits"
    assert entries[0].count == 2
    assert entries[0].distinct_questions == 2
    assert entries[1].department == "Facilities & Workplace"
    assert entries[1].count == 1


def test_department_gap_report_groups_unrouted_misses_together(tmp_path):
    log = MissLog(tmp_path / "misses.db")
    _seed(log, "jordan-rivera", "What's your favorite pizza topping?")
    _seed(log, "alex-chen", "Will I get stock options?")

    entries = department_gap_report(log)

    assert entries[0].department == UNROUTED_LABEL
    assert entries[0].count == 2


def test_department_gap_report_empty_log_returns_empty(tmp_path):
    log = MissLog(tmp_path / "misses.db")

    assert department_gap_report(log) == []
