"""Tests for weighted exam sampling."""

import random
from collections import Counter

from databricklings.content import load_domains
from databricklings.models import Question
from databricklings.sampling import EXAM_SIZE, sample_drill, sample_exam, weighted_counts


def make_question(qid: str, domain: int, subtopic: str = "x") -> Question:
    """Build a minimal valid Question for sampling tests."""
    return Question(
        id=qid,
        domain=domain,
        subtopic=subtopic,
        difficulty="medium",
        type="multiple_choice",
        stem="stem",
        options=["a", "b", "c", "d"],
        answer=[0],
        explanation="because",
    )


def make_pool(per_domain: int = 40) -> list[Question]:
    """Build a pool with per_domain questions in each of the 10 domains."""
    return [make_question(f"d{d:02d}-q{i:03d}", d) for d in range(1, 11) for i in range(per_domain)]


def test_weighted_counts_sum_to_total():
    """Largest remainder split always sums to the requested total."""
    domains = load_domains()
    counts = weighted_counts(domains, EXAM_SIZE)
    assert sum(counts.values()) == EXAM_SIZE


def test_weighted_counts_match_weights():
    """Each domain gets floor or ceil of its exact weighted share."""
    domains = load_domains()
    counts = weighted_counts(domains, EXAM_SIZE)
    for d in domains:
        exact = EXAM_SIZE * d.weight / 100
        assert int(exact) <= counts[d.id] <= int(exact) + 1


def test_exam_respects_domain_counts():
    """Sampled exam contains exactly the weighted count per domain."""
    domains = load_domains()
    pool = make_pool()
    exam = sample_exam(pool, domains, rng=random.Random(42))
    counts = weighted_counts(domains, EXAM_SIZE)
    got = Counter(q.domain for q in exam)
    assert len(exam) == EXAM_SIZE
    assert dict(got) == counts


def test_exam_no_duplicates():
    """An exam never contains the same question twice."""
    domains = load_domains()
    exam = sample_exam(make_pool(), domains, rng=random.Random(7))
    assert len({q.id for q in exam}) == EXAM_SIZE


def test_exam_fills_shortfall_from_other_domains():
    """When a domain has too few questions the exam still reaches full size."""
    domains = load_domains()
    pool = [q for q in make_pool() if q.domain != 1] + [make_question("d01-q001", 1)]
    exam = sample_exam(pool, domains, rng=random.Random(1))
    assert len(exam) == EXAM_SIZE


def test_drill_domain_filter():
    """Drill mode with a domain filter only returns that domain."""
    pool = make_pool()
    drill = sample_drill(pool, 10, domain=6, rng=random.Random(3))
    assert len(drill) == 10
    assert all(q.domain == 6 for q in drill)


def test_drill_weak_subtopics():
    """Drill mode prefers questions from weak subtopics when given."""
    pool = make_pool() + [make_question(f"weak-{i}", 1, subtopic="skew") for i in range(12)]
    drill = sample_drill(pool, 10, weak_subtopics={"skew"}, rng=random.Random(3))
    assert all(q.subtopic == "skew" for q in drill)
