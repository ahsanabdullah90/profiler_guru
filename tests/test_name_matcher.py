"""Tests for the fuzzy name matching service."""

from src.services.name_matcher import compute_name_similarity, find_similar_contacts


def test_exact_match():
    """Same name (case-insensitive) should score near 1.0."""
    assert compute_name_similarity("Sarah", "sarah") > 0.9


def test_substring_token_match():
    """Shorter name contained as a token in a longer name is a strong match."""
    assert compute_name_similarity("Sarah", "sarah_johnson") > 0.9
    assert compute_name_similarity("sarah_johnson", "Sarah") > 0.9


def test_nickname_variant():
    """Nickname variations like John/Johnny should score above threshold."""
    assert compute_name_similarity("John", "Johnny") > 0.72


def test_word_reordering():
    """Same tokens in different order should match perfectly."""
    assert compute_name_similarity("John Smith", "Smith John") > 0.9


def test_title_stripping():
    """Title prefixes like 'Dr.' should not prevent matching."""
    score = compute_name_similarity("Dr. Sarah", "Sarah")
    assert score > 0.72, f"Expected >0.72, got {score}"


def test_typo_tolerance():
    """Small typos (Sara vs Sarah) should still match."""
    assert compute_name_similarity("Sara", "Sarah") > 0.72


def test_underscore_normalization():
    """Names with underscores should match non-underscore variants."""
    assert compute_name_similarity("TestUser", "test_user") > 0.72


def test_different_names():
    """Completely different names should score below threshold."""
    assert compute_name_similarity("Mike", "Michael") < 0.72
    assert compute_name_similarity("John", "Jane") < 0.72


def test_totally_unrelated():
    """No similarity at all."""
    assert compute_name_similarity("Alice", "Bob") < 0.5


def test_find_similar_contacts():
    """find_similar_contacts should return matching contacts sorted by score."""
    results = find_similar_contacts("John", ["Johnny", "Jane", "Bob"], threshold=0.72)
    assert len(results) == 1, f"Expected 1 match, got {len(results)}"
    assert results[0][0] == "Johnny"


def test_find_similar_empty():
    """Empty inputs return empty lists."""
    assert find_similar_contacts("", ["A", "B"]) == []
    assert find_similar_contacts("X", []) == []


def test_exact_duplicate_handling():
    """Same exact name should match at 1.0."""
    results = find_similar_contacts("Sarah", ["sarah", "Bob", "Alice"], threshold=0.72)
    matches = [n for n, s in results]
    assert "sarah" in matches


def test_no_false_positive():
    """Ensure unrelated names don't match."""
    results = find_similar_contacts("unknown_name_123", ["Sarah", "John"], threshold=0.72)
    assert len(results) == 0
