"""Parse structured scores and classifications from LLM-generated markdown."""

import json
import re
from typing import Any

_SCORES_RE = re.compile(r"<!--\s*SCORES:\s*(.*?)\s*-->", re.DOTALL)
_CLASSIFICATION_RE = re.compile(r"<!--\s*CLASSIFICATION:\s*(.*?)\s*-->", re.DOTALL)

_ERROR_PROFILE_PATTERNS = [
    "Error:",
    "is not reachable",
    "failed to generate",
    "HTTP Error",
    "Ollama generation failed",
    "Traceback (most recent call last)",
]


def is_error_profile(profile_text: str | None) -> bool:
    """Check if a profile string contains an error message instead of a valid assessment."""
    if not profile_text:
        return False
    return any(p in profile_text for p in _ERROR_PROFILE_PATTERNS)


def parse_scores(markdown: str) -> dict[str, int | float] | None:
    """Extract the first <!-- SCORES: {...} --> block and parse it as JSON.

    Returns a dict of dimension_id -> score, or None if not found or invalid.
    """
    match = _SCORES_RE.search(markdown)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data: dict[str, int | float] = json.loads(raw)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def parse_classification(markdown: str) -> str | None:
    """Extract the first <!-- CLASSIFICATION: value --> block.

    Returns the classification string or None.
    """
    match = _CLASSIFICATION_RE.search(markdown)
    if not match:
        return None
    return match.group(1).strip()


def strip_score_blocks(markdown: str) -> str:
    """Remove all <!-- ... --> score/classification blocks from the markdown.
    Returns the original markdown if stripping everything would leave it empty."""
    stripped = _SCORES_RE.sub("", _CLASSIFICATION_RE.sub("", markdown)).strip()
    return stripped if stripped else markdown.strip()


def parse_assessment_output(markdown: str, framework_id: str) -> dict[str, Any]:
    """Parse the full LLM assessment output into structured data.

    Returns:
        {
            "narrative": str,           # Full markdown with score blocks stripped
            "scores": dict | None,       # parsed scores or None
            "classification": str | None # classification (attachment only)
        }
    """
    scores = parse_scores(markdown)
    classification = parse_classification(markdown) if framework_id == "attachment" else None
    narrative = strip_score_blocks(markdown)
    return {
        "narrative": narrative,
        "scores": scores,
        "classification": classification,
    }
