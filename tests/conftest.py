"""Shared fixtures: a small but complete content directory on disk."""

import shutil
from pathlib import Path

import pytest
import yaml

REAL_CONTENT = Path(__file__).resolve().parent.parent / "content"


def fixture_lesson(domain: int, order: int) -> dict:
    """Build one minimal valid lesson dict."""
    lesson_id = f"d{domain:02d}-l{order:02d}"
    return {
        "id": lesson_id,
        "domain": domain,
        "order": order,
        "title": f"lesson {lesson_id}",
        "body": "Some study text.\n\n```python\nspark.read.table('t')\n```\n",
        "exercises": [
            {
                "type": "mcq",
                "prompt": "Pick a.",
                "options": ["right", "wrong", "also wrong"],
                "answer": [0],
                "explanation": "a is right because the fixture says so.",
            },
            {
                "type": "multi",
                "prompt": "Pick a and b.",
                "options": ["one", "two", "three"],
                "answer": [0, 1],
                "explanation": "a and b, fixture rules.",
            },
            {
                "type": "fill_blank",
                "prompt": "Type the trigger name for one-shot streaming.",
                "answers": ["availableNow"],
                "explanation": "availableNow processes everything then stops.",
            },
        ],
    }


def fixture_question(domain: int, num: int) -> dict:
    """Build one minimal valid question dict."""
    return {
        "id": f"d{domain:02d}-q{num:03d}",
        "domain": domain,
        "subtopic": f"topic-{domain}",
        "difficulty": "medium",
        "type": "multiple_choice",
        "stem": f"Fixture question {num} for domain {domain}. Which option is correct?",
        "options": ["correct", "plausible", "tempting", "wrong"],
        "answer": [0],
        "explanation": "Option a is correct by fixture construction, the rest are filler.",
    }


@pytest.fixture
def content_dir(tmp_path: Path) -> Path:
    """Write a complete fixture content tree with 2 lessons/domain and 8 questions/domain."""
    root = tmp_path / "content"
    (root / "lessons").mkdir(parents=True)
    (root / "questions").mkdir()
    shutil.copy(REAL_CONTENT / "domains.yaml", root / "domains.yaml")
    for domain in range(1, 11):
        for order in (1, 2):
            lesson = fixture_lesson(domain, order)
            (root / "lessons" / f"{lesson['id']}.yaml").write_text(yaml.safe_dump(lesson))
        questions = [fixture_question(domain, n) for n in range(1, 9)]
        (root / "questions" / f"d{domain:02d}.yaml").write_text(yaml.safe_dump({"questions": questions}))
    return root
