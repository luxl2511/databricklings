"""Tests for fuzzy filtering."""

from databricklings.fuzzy import fuzzy_filter, fuzzy_score


def test_subsequence_matches():
    """Characters must appear in order, gaps allowed."""
    assert fuzzy_score("alo", "auto loader") is not None
    assert fuzzy_score("xyz", "auto loader") is None


def test_empty_query_matches_all():
    """Empty query keeps every item."""
    assert fuzzy_filter("", ["a", "b"]) == ["a", "b"]


def test_consecutive_matches_rank_higher():
    """Tight matches beat scattered ones."""
    items = ["delta lake merge", "deduplicate streams"]
    assert fuzzy_filter("merge", items)[0] == "delta lake merge"
