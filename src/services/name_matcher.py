import difflib
import re

_WORD_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(name: str) -> set[str]:
    return set(_WORD_RE.findall(name.lower()))


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    intersection = a & b
    union = a | b
    return len(intersection) / len(union)


def _sequence_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _best_partial_match(name_a: str, name_b: str) -> float:
    """Best similarity of the shorter name against any token in the longer name."""
    tokens_a = _WORD_RE.findall(name_a.lower())
    tokens_b = _WORD_RE.findall(name_b.lower())
    if not tokens_a or not tokens_b:
        return 0.0
    # Use the name with fewer tokens as the query, more tokens as the target.
    # If same count, compare both ways and take the max.
    if len(tokens_a) <= len(tokens_b):
        query_tokens, target_tokens = tokens_a, tokens_b
    else:
        query_tokens, target_tokens = tokens_b, tokens_a
    short_full = " ".join(query_tokens)
    best = 0.0
    for tt in target_tokens:
        score = difflib.SequenceMatcher(None, short_full, tt).ratio()
        if score > best:
            best = score
    # If same token count, also try the reverse direction to avoid self-match
    if len(tokens_a) == len(tokens_b) and len(tokens_a) > 0:
        rev_full = " ".join(target_tokens)
        for qt in query_tokens:
            score = difflib.SequenceMatcher(None, rev_full, qt).ratio()
            if score > best:
                best = score
    return best


def compute_name_similarity(name_a: str, name_b: str) -> float:
    """Compute similarity between two names (0.0 – 1.0).

    Uses the best of:
    - character-level SequenceMatcher on full names
    - partial match (short name vs tokens of long name)
    - token Jaccard similarity (handles word reordering like 'John Smith' vs 'Smith John')
    """
    seq_score = _sequence_similarity(name_a, name_b)
    partial_score = _best_partial_match(name_a, name_b)
    tokens_a = _tokenize(name_a)
    tokens_b = _tokenize(name_b)
    jaccard = _jaccard_similarity(tokens_a, tokens_b)

    return max(seq_score, partial_score, jaccard)


def find_similar_contacts(
    new_name: str,
    existing_names: list[str],
    threshold: float = 0.72,
) -> list[tuple[str, float]]:
    """Find existing contacts whose name is similar to `new_name`.

    Returns list of (existing_name, similarity_score) tuples sorted by score descending.
    Only returns matches above `threshold`.
    """
    if not new_name or not existing_names:
        return []

    scores: list[tuple[str, float]] = []
    for existing in existing_names:
        if existing.lower().replace("_", "").replace(" ", "") == new_name.lower().replace("_", "").replace(" ", ""):
            score = 1.0
        else:
            score = compute_name_similarity(new_name, existing)
        if score >= threshold:
            scores.append((existing, score))

    scores.sort(key=lambda x: x[1], reverse=True)
    return scores
