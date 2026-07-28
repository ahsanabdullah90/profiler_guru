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


def _normalize_score_value(val: Any) -> int | float:
    """Extract a numeric score from either flat format or nested {score, confidence, evidence_count} format."""
    if isinstance(val, dict):
        return int(val.get("score", 0))
    return int(val)


def parse_scores(markdown: str) -> dict[str, int | float] | None:
    """Extract the first <!-- SCORES: {...} --> block and parse it as JSON.

    Supports both flat format ``{"dim": 7}`` and nested format
    ``{"dim": {"score": 7, "confidence": 0.8, "evidence_count": 5}}``.
    Returns a dict of dimension_id -> numeric score, or None if not found/invalid.
    """
    match = _SCORES_RE.search(markdown)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data: dict[str, Any] = json.loads(raw)
        if isinstance(data, dict):
            return {k: _normalize_score_value(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def parse_score_metadata(markdown: str) -> dict[str, dict[str, Any]] | None:
    """Extract detailed score metadata from the first <!-- SCORES: {...} --> block.

    Returns a dict of dimension_id -> {score, confidence, evidence_count}
    for the nested format. Falls back to {score} only for flat format.
    Returns None if no score block is found.
    """
    match = _SCORES_RE.search(markdown)
    if not match:
        return None
    raw = match.group(1).strip()
    try:
        data: dict[str, Any] = json.loads(raw)
        if not isinstance(data, dict):
            return None
        result: dict[str, dict[str, Any]] = {}
        for k, v in data.items():
            if isinstance(v, dict):
                result[k] = {
                    "score": int(v.get("score", 0)),
                    "confidence": float(v.get("confidence", 0.0)),
                    "evidence_count": int(v.get("evidence_count", 0)),
                }
            else:
                result[k] = {"score": int(v), "confidence": 0.0, "evidence_count": 0}
        return result
    except (json.JSONDecodeError, TypeError, ValueError):
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
            "scores": dict | None,       # parsed scores (flat) or None
            "score_metadata": dict | None, # detailed score info with confidence/evidence
            "classification": str | None # classification (attachment only)
        }
    """
    scores = parse_scores(markdown)
    score_metadata = parse_score_metadata(markdown)
    classification = parse_classification(markdown) if framework_id == "attachment" else None
    narrative = strip_score_blocks(markdown)
    return {
        "narrative": narrative,
        "scores": scores,
        "score_metadata": score_metadata,
        "classification": classification,
    }
