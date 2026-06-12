"""Tests for progress persistence."""

from databricklings.progress import (
    Progress,
    lesson_state,
    load_progress,
    record_answer,
    record_exam,
    record_exercise_pass,
    record_lesson_complete,
    save_progress,
)


def test_roundtrip(tmp_path):
    """Save then load returns the same data."""
    path = tmp_path / "progress.json"
    p = Progress()
    record_exercise_pass(p, "d01-l01", "d01-l01-e1")
    record_lesson_complete(p, "d01-l01")
    record_answer(p, "d01-q001", True, "exam")
    record_exam(p, {"score": 50, "total": 59})
    save_progress(p, path)
    loaded = load_progress(path)
    assert loaded.lessons["d01-l01"]["passed"] == ["d01-l01-e1"]
    assert loaded.lessons["d01-l01"]["completed_at"] is not None
    assert loaded.questions["d01-q001"]["history"][0]["correct"] is True
    assert loaded.exams[0]["score"] == 50


def test_missing_file_returns_empty(tmp_path):
    """Loading a nonexistent file yields empty Progress."""
    loaded = load_progress(tmp_path / "nope.json")
    assert loaded.lessons == {} and loaded.exams == []


def test_corrupt_file_returns_empty(tmp_path):
    """Loading corrupt json yields empty Progress instead of crashing."""
    path = tmp_path / "progress.json"
    path.write_text("{not json")
    assert load_progress(path).questions == {}


def test_exercise_pass_idempotent(tmp_path):
    """Passing the same exercise twice records it once."""
    p = Progress()
    record_exercise_pass(p, "l1", "e1")
    record_exercise_pass(p, "l1", "e1")
    assert p.lessons["l1"]["passed"] == ["e1"]


def test_lesson_state():
    """Lesson state reflects passed exercises and completion."""
    p = Progress()
    assert lesson_state(p, "l1", 4) == "open"
    record_exercise_pass(p, "l1", "e1")
    assert lesson_state(p, "l1", 4) == "partial"
    record_lesson_complete(p, "l1")
    assert lesson_state(p, "l1", 4) == "done"
