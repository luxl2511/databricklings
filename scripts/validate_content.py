"""Validate all content files and print per-domain counts and verify flags."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from databricklings.content import ContentError, load_domains, load_lessons, load_questions


def main() -> int:
    """Load everything, print counts, return nonzero on validation errors."""
    try:
        domains = load_domains()
        lessons = load_lessons()
        questions = load_questions()
    except ContentError as err:
        print(f"INVALID: {err}")
        return 1
    lesson_counts = Counter(l.domain for l in lessons)
    question_counts = Counter(q.domain for q in questions)
    print(f"{'domain':<50} {'lessons':>8} {'questions':>10}")
    for d in domains:
        print(f"D{d.id:<2} {d.name:<46.46} {lesson_counts.get(d.id, 0):>8} {question_counts.get(d.id, 0):>10}")
    print(f"{'total':<50} {len(lessons):>8} {len(questions):>10}")
    flagged = [l.id for l in lessons if l.verify]
    flagged += [ex.id for l in lessons for ex in l.exercises if ex.verify]
    flagged += [q.id for q in questions if q.verify]
    if flagged:
        print(f"\nverify flagged ({len(flagged)}):")
        for item in flagged:
            print(f"  {item}")
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
