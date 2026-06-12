"""Telescope-like fuzzy subsequence matching for list filtering."""


def fuzzy_score(query: str, text: str) -> int | None:
    """Score a subsequence match, higher is better, none when query does not match."""
    if not query:
        return 0
    q = query.lower()
    t = text.lower()
    score = 0
    pos = -1
    streak = 0
    for ch in q:
        found = t.find(ch, pos + 1)
        if found == -1:
            return None
        streak = streak + 1 if found == pos + 1 else 1
        score += streak * 2 - (found - pos)
        pos = found
    return score


def fuzzy_filter(query: str, items: list, key=str) -> list:
    """Filter and rank items by fuzzy match against the query."""
    scored = []
    for item in items:
        s = fuzzy_score(query, key(item))
        if s is not None:
            scored.append((s, item))
    scored.sort(key=lambda pair: -pair[0])
    return [item for _, item in scored]
