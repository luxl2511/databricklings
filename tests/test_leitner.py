"""Tests for Leitner spaced repetition scheduling."""

from datetime import datetime, timedelta, timezone

from databricklings.leitner import due_question_ids, in_review_count, schedule_after_answer
from databricklings.progress import Progress

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc)


def test_wrong_answer_enters_box_one():
    """A wrong answer puts the question into box 1, due immediately."""
    p = Progress()
    schedule_after_answer(p, "q1", correct=False, now=NOW)
    assert p.questions["q1"]["box"] == 1
    assert due_question_ids(p, now=NOW) == ["q1"]


def test_correct_answer_outside_queue_stays_outside():
    """A correct answer on a never-wrong question does not enter the queue."""
    p = Progress()
    schedule_after_answer(p, "q1", correct=True, now=NOW)
    assert p.questions["q1"]["box"] == 0
    assert due_question_ids(p, now=NOW) == []


def test_correct_advances_box_and_due_date():
    """Correct answers move the question up one box with a longer interval."""
    p = Progress()
    schedule_after_answer(p, "q1", correct=False, now=NOW)
    schedule_after_answer(p, "q1", correct=True, now=NOW)
    assert p.questions["q1"]["box"] == 2
    assert due_question_ids(p, now=NOW) == []
    assert due_question_ids(p, now=NOW + timedelta(days=1)) == ["q1"]


def test_wrong_resets_to_box_one():
    """A wrong answer drops the question back to box 1."""
    p = Progress()
    schedule_after_answer(p, "q1", correct=False, now=NOW)
    schedule_after_answer(p, "q1", correct=True, now=NOW)
    schedule_after_answer(p, "q1", correct=False, now=NOW)
    assert p.questions["q1"]["box"] == 1


def test_box_five_graduates():
    """Answering correctly in box 5 removes the question from the queue."""
    p = Progress()
    schedule_after_answer(p, "q1", correct=False, now=NOW)
    for _ in range(4):
        schedule_after_answer(p, "q1", correct=True, now=NOW)
    assert p.questions["q1"]["box"] == 5
    schedule_after_answer(p, "q1", correct=True, now=NOW)
    assert p.questions["q1"]["box"] == 0
    assert in_review_count(p) == 0


def test_due_sorted_lowest_box_first():
    """Due list puts box 1 questions before higher boxes."""
    p = Progress()
    schedule_after_answer(p, "q_high", correct=False, now=NOW - timedelta(days=2))
    schedule_after_answer(p, "q_high", correct=True, now=NOW - timedelta(days=2))
    schedule_after_answer(p, "q_low", correct=False, now=NOW)
    assert due_question_ids(p, now=NOW) == ["q_low", "q_high"]
