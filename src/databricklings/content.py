"""Load and validate domains, lessons and questions from the content directory."""

from pathlib import Path

import yaml

from databricklings.models import CHOICE_TYPES, Domain, Exercise, Lesson, Question

CONTENT_DIR = Path(__file__).resolve().parent.parent.parent / "content"
EXERCISE_TYPES = {"mcq", "multi", "predict_output", "spot_bug", "fill_blank"}
QUESTION_TYPES = {"multiple_choice", "multi_select"}
DIFFICULTIES = {"easy", "medium", "hard"}


class ContentError(Exception):
    """Raised when a content file fails validation."""


def load_domains(content_dir: Path = CONTENT_DIR) -> list[Domain]:
    """Load domain list from domains.yaml ordered by id."""
    raw = yaml.safe_load((content_dir / "domains.yaml").read_text())
    domains = [Domain(**d) for d in raw["domains"]]
    total = sum(d.weight for d in domains)
    if total != 100:
        raise ContentError(f"domain weights sum to {total}, expected 100")
    return sorted(domains, key=lambda d: d.id)


def parse_exercise(raw: dict, lesson_id: str, index: int) -> Exercise:
    """Build one Exercise from raw yaml and validate its fields."""
    ex = Exercise(
        id=raw.get("id", f"{lesson_id}-e{index + 1}"),
        type=raw["type"],
        prompt=raw["prompt"],
        options=[str(o) for o in raw.get("options", [])],
        answer=list(raw.get("answer", [])),
        answers=[str(a) for a in raw.get("answers", [])],
        explanation=raw.get("explanation", ""),
        code=raw.get("code", ""),
        code_lang=raw.get("code_lang", "python"),
        verify=bool(raw.get("verify", False)),
    )
    if ex.type not in EXERCISE_TYPES:
        raise ContentError(f"{ex.id}: unknown exercise type {ex.type}")
    if ex.is_fill_blank():
        if not ex.answers:
            raise ContentError(f"{ex.id}: fill_blank needs accepted answers")
    else:
        check_choices(ex.id, ex.options, ex.answer)
    if not ex.explanation:
        raise ContentError(f"{ex.id}: missing explanation")
    return ex


def check_choices(item_id: str, options: list[str], answer: list[int]) -> None:
    """Validate that answer indices exist and options are plentiful enough."""
    if len(options) < 2:
        raise ContentError(f"{item_id}: needs at least 2 options")
    if not answer:
        raise ContentError(f"{item_id}: missing answer")
    for idx in answer:
        if not 0 <= idx < len(options):
            raise ContentError(f"{item_id}: answer index {idx} out of range")
    if len(set(answer)) != len(answer):
        raise ContentError(f"{item_id}: duplicate answer indices")


def parse_lesson(raw: dict) -> Lesson:
    """Build one Lesson from raw yaml and validate it."""
    lesson_id = raw["id"]
    exercises = [parse_exercise(e, lesson_id, i) for i, e in enumerate(raw.get("exercises", []))]
    if not 3 <= len(exercises) <= 6:
        raise ContentError(f"{lesson_id}: needs 3-6 exercises, has {len(exercises)}")
    return Lesson(
        id=lesson_id,
        domain=int(raw["domain"]),
        order=int(raw["order"]),
        title=raw["title"],
        body=raw["body"],
        exercises=exercises,
        verify=bool(raw.get("verify", False)),
    )


def load_lessons(content_dir: Path = CONTENT_DIR) -> list[Lesson]:
    """Load all lesson yaml files sorted by domain then order."""
    lessons = []
    for path in sorted((content_dir / "lessons").rglob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        try:
            lessons.append(parse_lesson(raw))
        except (ContentError, KeyError, TypeError) as err:
            raise ContentError(f"{path.name}: {err}") from err
    seen = set()
    for lesson in lessons:
        if lesson.id in seen:
            raise ContentError(f"duplicate lesson id {lesson.id}")
        seen.add(lesson.id)
    return sorted(lessons, key=lambda l: (l.domain, l.order))


def parse_question(raw: dict) -> Question:
    """Build one Question from raw yaml and validate it."""
    q = Question(
        id=raw["id"],
        domain=int(raw["domain"]),
        subtopic=raw["subtopic"],
        difficulty=raw["difficulty"],
        type=raw["type"],
        stem=raw["stem"],
        options=[str(o) for o in raw["options"]],
        answer=list(raw["answer"]),
        explanation=raw["explanation"],
        code=raw.get("code", ""),
        code_lang=raw.get("code_lang", "python"),
        verify=bool(raw.get("verify", False)),
    )
    if q.type not in QUESTION_TYPES:
        raise ContentError(f"{q.id}: unknown question type {q.type}")
    if q.difficulty not in DIFFICULTIES:
        raise ContentError(f"{q.id}: unknown difficulty {q.difficulty}")
    if q.type == "multiple_choice" and len(q.answer) != 1:
        raise ContentError(f"{q.id}: multiple_choice needs exactly one answer")
    check_choices(q.id, q.options, q.answer)
    if not q.explanation:
        raise ContentError(f"{q.id}: missing explanation")
    return q


def load_questions(content_dir: Path = CONTENT_DIR) -> list[Question]:
    """Load all question yaml files from the questions directory."""
    questions = []
    for path in sorted((content_dir / "questions").glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        for entry in raw["questions"]:
            try:
                questions.append(parse_question(entry))
            except (ContentError, KeyError, TypeError) as err:
                raise ContentError(f"{path.name}: {err}") from err
    seen = set()
    for q in questions:
        if q.id in seen:
            raise ContentError(f"duplicate question id {q.id}")
        seen.add(q.id)
    return questions
