"""Weighted question sampling for exam and drill modes."""

import random
from collections import defaultdict

from databricklings.models import Domain, Question

EXAM_SIZE = 59
EXAM_MINUTES = 120


def weighted_counts(domains: list[Domain], total: int) -> dict[int, int]:
    """Split total question count over domains by weight using largest remainder."""
    exact = {d.id: total * d.weight / 100 for d in domains}
    counts = {did: int(v) for did, v in exact.items()}
    remainder = total - sum(counts.values())
    by_fraction = sorted(exact, key=lambda did: exact[did] - counts[did], reverse=True)
    for did in by_fraction[:remainder]:
        counts[did] += 1
    return counts


def sample_exam(
    questions: list[Question],
    domains: list[Domain],
    total: int = EXAM_SIZE,
    rng: random.Random | None = None,
) -> list[Question]:
    """Sample an exam weighted by domain, fill shortfalls from remaining pool, shuffled."""
    rng = rng or random.Random()
    counts = weighted_counts(domains, total)
    pool = defaultdict(list)
    for q in questions:
        pool[q.domain].append(q)
    picked = []
    for did, count in counts.items():
        available = pool[did]
        take = min(count, len(available))
        picked.extend(rng.sample(available, take))
    if len(picked) < total:
        picked_ids = {q.id for q in picked}
        rest = [q for q in questions if q.id not in picked_ids]
        picked.extend(rng.sample(rest, min(total - len(picked), len(rest))))
    rng.shuffle(picked)
    return picked


def sample_drill(
    questions: list[Question],
    count: int,
    domain: int | None = None,
    weak_subtopics: set[str] | None = None,
    rng: random.Random | None = None,
) -> list[Question]:
    """Sample a drill set, optionally filtered by domain or weak subtopics."""
    rng = rng or random.Random()
    pool = questions
    if domain is not None:
        pool = [q for q in pool if q.domain == domain]
    if weak_subtopics:
        weak = [q for q in pool if q.subtopic in weak_subtopics]
        if weak:
            pool = weak
    return rng.sample(pool, min(count, len(pool)))
