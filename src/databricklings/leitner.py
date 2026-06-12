"""Leitner box spaced repetition over the question history in Progress."""

from datetime import datetime, timedelta, timezone

from databricklings.progress import Progress, now_iso

BOX_INTERVALS_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}
MAX_BOX = 5


def schedule_after_answer(progress: Progress, question_id: str, correct: bool, now: datetime | None = None) -> None:
    """Update Leitner box and due date for a question after an answer."""
    now = now or datetime.now(timezone.utc)
    entry = progress.questions.setdefault(question_id, {"box": 0, "due": None, "history": []})
    box = entry.get("box", 0)
    if not correct:
        entry["box"] = 1
        entry["due"] = now.isoformat()
        return
    if box == 0:
        return
    if box >= MAX_BOX:
        entry["box"] = 0
        entry["due"] = None
        return
    new_box = box + 1
    entry["box"] = new_box
    entry["due"] = (now + timedelta(days=BOX_INTERVALS_DAYS[new_box])).isoformat()


def due_question_ids(progress: Progress, now: datetime | None = None) -> list[str]:
    """Return ids of all review questions due now, lowest box first."""
    now = now or datetime.now(timezone.utc)
    due = []
    for qid, entry in progress.questions.items():
        if entry.get("box", 0) < 1 or entry.get("due") is None:
            continue
        if datetime.fromisoformat(entry["due"]) <= now:
            due.append((entry["box"], qid))
    return [qid for _, qid in sorted(due)]


def in_review_count(progress: Progress) -> int:
    """Return how many questions currently sit in a Leitner box."""
    return sum(1 for e in progress.questions.values() if e.get("box", 0) >= 1)
