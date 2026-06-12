"""Tests for scoring and weak-spot detection."""

from databricklings.progress import Progress, record_answer
from databricklings.scoring import (
    domain_accuracy,
    is_correct,
    is_fill_correct,
    score_exam,
    weak_subtopics,
)
from tests.test_sampling import make_question


def test_is_correct_exact_set_match():
    """Multi-select needs the exact answer set, order does not matter."""
    q = make_question("q1", 1)
    multi = make_question("q2", 1)
    object.__setattr__(multi, "answer", [0, 2])
    assert is_correct(q, [0]) is True
    assert is_correct(q, [1]) is False
    assert is_correct(multi, [2, 0]) is True
    assert is_correct(multi, [0]) is False
    assert is_correct(multi, [0, 1, 2]) is False


def test_is_fill_correct_normalizes():
    """Fill-in answers match case-insensitive and trimmed."""
    assert is_fill_correct(["availableNow"], "  AVAILABLENOW ") is True
    assert is_fill_correct(["availableNow"], "available_now") is False


def test_score_exam_breakdown():
    """Exam scoring counts per domain and treats unanswered as wrong."""
    qs = [make_question("q1", 1), make_question("q2", 1), make_question("q3", 6)]
    result = score_exam(qs, {"q1": [0], "q2": [1]})
    assert result["score"] == 1
    assert result["total"] == 3
    assert result["per_domain"]["1"] == {"correct": 1, "total": 2}
    assert result["per_domain"]["6"] == {"correct": 0, "total": 1}
    unanswered = [a for a in result["answers"] if a["qid"] == "q3"][0]
    assert unanswered["correct"] is False


def test_domain_accuracy_from_history():
    """Per-domain accuracy aggregates the full answer history."""
    qs = [make_question("q1", 1), make_question("q2", 6)]
    p = Progress()
    record_answer(p, "q1", True, "drill")
    record_answer(p, "q1", False, "drill")
    record_answer(p, "q2", True, "exam")
    scores = {s.domain: s for s in domain_accuracy(p, qs)}
    assert scores[1].correct == 1 and scores[1].total == 2
    assert scores[6].pct() == 100.0


def test_weak_subtopics_threshold():
    """Subtopics below the accuracy threshold with enough attempts are weak."""
    qs = [make_question("q1", 1, subtopic="udf"), make_question("q2", 1, subtopic="merge")]
    p = Progress()
    record_answer(p, "q1", False, "drill")
    record_answer(p, "q1", False, "drill")
    record_answer(p, "q2", True, "drill")
    record_answer(p, "q2", True, "drill")
    assert weak_subtopics(p, qs) == {"udf"}
