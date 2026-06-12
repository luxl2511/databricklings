"""Persist lesson, question and exam progress in a single json file."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROGRESS_DIR = Path.home() / ".databricklings"
PROGRESS_FILE = PROGRESS_DIR / "progress.json"


@dataclass
class Progress:
    """In-memory progress state, mirrors the json file layout."""

    lessons: dict = field(default_factory=dict)
    questions: dict = field(default_factory=dict)
    exams: list = field(default_factory=list)
    version: int = 1


def now_iso() -> str:
    """Return the current utc time as iso string."""
    return datetime.now(timezone.utc).isoformat()


def load_progress(path: Path = PROGRESS_FILE) -> Progress:
    """Load progress from json file, return empty Progress when missing or corrupt."""
    if not path.exists():
        return Progress()
    try:
        raw = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return Progress()
    return Progress(
        lessons=raw.get("lessons", {}),
        questions=raw.get("questions", {}),
        exams=raw.get("exams", []),
        version=raw.get("version", 1),
    )


def save_progress(progress: Progress, path: Path = PROGRESS_FILE) -> None:
    """Write progress to json file, creating the directory if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": progress.version,
        "lessons": progress.lessons,
        "questions": progress.questions,
        "exams": progress.exams,
    }
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(path)


def record_exercise_pass(progress: Progress, lesson_id: str, exercise_id: str) -> None:
    """Mark one exercise of a lesson as passed."""
    entry = progress.lessons.setdefault(lesson_id, {"passed": [], "completed_at": None})
    if exercise_id not in entry["passed"]:
        entry["passed"].append(exercise_id)


def record_lesson_complete(progress: Progress, lesson_id: str) -> None:
    """Mark a lesson as completed with a timestamp."""
    entry = progress.lessons.setdefault(lesson_id, {"passed": [], "completed_at": None})
    if entry["completed_at"] is None:
        entry["completed_at"] = now_iso()


def lesson_state(progress: Progress, lesson_id: str, total_exercises: int) -> str:
    """Return done, partial or locked-agnostic open state for a lesson."""
    entry = progress.lessons.get(lesson_id)
    if entry is None:
        return "open"
    if entry["completed_at"] is not None:
        return "done"
    if entry["passed"]:
        return "partial"
    return "open"


def record_answer(progress: Progress, question_id: str, correct: bool, mode: str) -> None:
    """Append one answer attempt to a question's history."""
    entry = progress.questions.setdefault(question_id, {"box": 0, "due": None, "history": []})
    entry["history"].append({"ts": now_iso(), "correct": correct, "mode": mode})


def record_exam(progress: Progress, result: dict) -> None:
    """Append one finished exam result."""
    progress.exams.append(result)
