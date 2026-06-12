"""Score answers and compute per-domain breakdowns and weak spots."""

from dataclasses import dataclass

from databricklings.models import Question
from databricklings.progress import Progress


@dataclass(frozen=True)
class DomainScore:
    """Correct and total counts for one domain."""

    domain: int
    correct: int
    total: int

    def pct(self) -> float:
        """Return accuracy in percent, 0 when nothing answered."""
        return 100 * self.correct / self.total if self.total else 0.0


def is_correct(question: Question, given: list[int]) -> bool:
    """Return whether the given option indices exactly match the answer set."""
    return set(given) == set(question.answer)


def is_fill_correct(accepted: list[str], given: str) -> bool:
    """Return whether typed text matches any accepted answer, case-insensitive and trimmed."""
    norm = given.strip().lower()
    return any(norm == a.strip().lower() for a in accepted)


def score_exam(questions: list[Question], given: dict[str, list[int]]) -> dict:
    """Build an exam result dict with score and per-domain breakdown."""
    answers = []
    per_domain: dict[int, list[int]] = {}
    for q in questions:
        sel = given.get(q.id, [])
        ok = is_correct(q, sel) if sel else False
        answers.append({"qid": q.id, "given": sel, "correct": ok})
        stats = per_domain.setdefault(q.domain, [0, 0])
        stats[0] += int(ok)
        stats[1] += 1
    correct = sum(a["correct"] for a in answers)
    return {
        "score": correct,
        "total": len(questions),
        "pct": round(100 * correct / len(questions), 1) if questions else 0.0,
        "per_domain": {str(d): {"correct": c, "total": t} for d, (c, t) in sorted(per_domain.items())},
        "answers": answers,
    }


def domain_accuracy(progress: Progress, questions: list[Question]) -> list[DomainScore]:
    """Compute all-time per-domain accuracy from the answer history."""
    by_id = {q.id: q for q in questions}
    tally: dict[int, list[int]] = {}
    for qid, entry in progress.questions.items():
        q = by_id.get(qid)
        if q is None:
            continue
        stats = tally.setdefault(q.domain, [0, 0])
        for attempt in entry.get("history", []):
            stats[0] += int(attempt["correct"])
            stats[1] += 1
    return [DomainScore(d, c, t) for d, (c, t) in sorted(tally.items())]


def weak_subtopics(progress: Progress, questions: list[Question], threshold: float = 70.0, min_attempts: int = 2) -> set[str]:
    """Return subtopics whose all-time accuracy sits below the threshold."""
    by_id = {q.id: q for q in questions}
    tally: dict[str, list[int]] = {}
    for qid, entry in progress.questions.items():
        q = by_id.get(qid)
        if q is None:
            continue
        stats = tally.setdefault(q.subtopic, [0, 0])
        for attempt in entry.get("history", []):
            stats[0] += int(attempt["correct"])
            stats[1] += 1
    return {
        sub
        for sub, (c, t) in tally.items()
        if t >= min_attempts and 100 * c / t < threshold
    }
