"""Unified quiz item model so exercises and questions share one quiz engine."""

from dataclasses import dataclass

from databricklings.models import Exercise, Question


@dataclass(frozen=True)
class QuizItem:
    """One quizzable item, built from either an Exercise or a Question."""

    id: str
    domain: int
    kind: str
    stem: str
    options: list[str]
    answer: list[int]
    answers: list[str]
    multi: bool
    fill: bool
    explanation: str
    code: str = ""
    code_lang: str = "python"
    difficulty: str = ""
    subtopic: str = ""


KIND_LABELS = {
    "mcq": "multiple choice",
    "multi": "multi select",
    "predict_output": "predict the output",
    "spot_bug": "spot the bug",
    "fill_blank": "fill in the blank",
    "multiple_choice": "multiple choice",
    "multi_select": "multi select",
}


def from_exercise(ex: Exercise, domain: int) -> QuizItem:
    """Convert a lesson Exercise into a QuizItem."""
    return QuizItem(
        id=ex.id,
        domain=domain,
        kind=ex.type,
        stem=ex.prompt,
        options=ex.options,
        answer=ex.answer,
        answers=ex.answers,
        multi=ex.is_multi(),
        fill=ex.is_fill_blank(),
        explanation=ex.explanation,
        code=ex.code,
        code_lang=ex.code_lang,
    )


def from_question(q: Question) -> QuizItem:
    """Convert an exam Question into a QuizItem."""
    return QuizItem(
        id=q.id,
        domain=q.domain,
        kind=q.type,
        stem=q.stem,
        options=q.options,
        answer=q.answer,
        answers=[],
        multi=q.is_multi(),
        fill=False,
        explanation=q.explanation,
        code=q.code,
        code_lang=q.code_lang,
        difficulty=q.difficulty,
        subtopic=q.subtopic,
    )
