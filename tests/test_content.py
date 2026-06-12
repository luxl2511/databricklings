"""Validation of the real shipped content, skipped while content is empty."""

from collections import Counter

import pytest

from databricklings.content import CONTENT_DIR, load_domains, load_lessons, load_questions
from databricklings.sampling import EXAM_SIZE, weighted_counts


def has_content() -> bool:
    """Return whether any real lesson files exist yet."""
    return any((CONTENT_DIR / "lessons").rglob("*.yaml"))


pytestmark = pytest.mark.skipif(not has_content(), reason="content not generated yet")


def test_all_content_parses():
    """Every shipped lesson and question file parses and validates."""
    lessons = load_lessons()
    questions = load_questions()
    assert lessons and questions


def test_volume_targets():
    """Curriculum size matches the spec: 40-60 lessons, 250+ questions."""
    assert 40 <= len(load_lessons()) <= 60
    assert len(load_questions()) >= 250


def test_question_distribution_mirrors_weights():
    """Per-domain question share stays close to the official weight."""
    domains = load_domains()
    questions = load_questions()
    counts = Counter(q.domain for q in questions)
    total = len(questions)
    for d in domains:
        share = 100 * counts[d.id] / total
        assert abs(share - d.weight) < 3, f"domain {d.id}: {share:.1f}% vs weight {d.weight}%"


def test_exam_pool_sufficient_per_domain():
    """Every domain has at least the questions one weighted exam needs."""
    domains = load_domains()
    counts = Counter(q.domain for q in load_questions())
    needed = weighted_counts(domains, EXAM_SIZE)
    for d in domains:
        assert counts[d.id] >= needed[d.id], f"domain {d.id} too small for an exam"


def test_lessons_have_exercise_variety():
    """Lesson exercises use more than one exercise type overall."""
    types = {ex.type for lesson in load_lessons() for ex in lesson.exercises}
    assert {"mcq", "fill_blank"} <= types
    assert types & {"predict_output", "spot_bug"}


def test_unique_orders_within_domain():
    """Lesson order values are unique inside each domain."""
    lessons = load_lessons()
    seen = Counter((l.domain, l.order) for l in lessons)
    dupes = [key for key, n in seen.items() if n > 1]
    assert not dupes
