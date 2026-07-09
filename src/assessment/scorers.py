"""Deterministic scoring for clinical screening instruments (PHQ-9, GAD-7, BHS).

These are arithmetic scores — no LLM involved. The practitioner answers the
questionnaire items and the app calculates the total + cut-point band.
"""

from typing import Any

from src.assessment.frameworks import get_framework


def score_questionnaire(framework_id: str, responses: dict[str, int]) -> dict[str, Any]:
    """Score a clinical questionnaire from item responses.

    Args:
        framework_id: e.g. "phq9", "gad7", "bhs"
        responses: {item_id: value, ...} — the practitioner's answers.

    Returns:
        {
            "framework_id": str,
            "total": int,
            "band": str,
            "item_count": int,
            "responses": {item_id: value},
            "max_score": int,
        }

    Raises ValueError if the framework is not a questionnaire type
    or if responses are invalid.
    """
    fw = get_framework(framework_id)
    if not fw:
        raise ValueError(f"Unknown framework: {framework_id}")
    if fw.get("kind") != "questionnaire":
        raise ValueError(f"Framework '{framework_id}' is not a questionnaire type")

    items = fw.get("items", [])
    if not items:
        raise ValueError(f"Framework '{framework_id}' has no items defined")

    # Validate and score
    total = 0
    max_possible = 0
    scored_responses: dict[str, int] = {}

    for item in items:
        item_id = item["id"]
        raw_value = responses.get(item_id)
        if raw_value is None:
            raise ValueError(f"Missing response for item '{item_id}'")

        # Validate value is within response range
        valid_values = [r["value"] for r in item.get("responses", [])]
        if raw_value not in valid_values:
            raise ValueError(
                f"Invalid value {raw_value} for item '{item_id}'. "
                f"Valid values: {valid_values}"
            )

        # Apply reverse scoring if marked
        if item.get("reverse"):
            # For BHS: True=1 becomes 0, True=0 becomes 1 (item is hopelessness-coded)
            # Actually, for BHS reverse items: the True/False is already 1/0.
            # The "reverse" flag means: the response value should be inverted.
            # If response is 1 (True for pessimism), score is actually 0
            # If response is 0 (False for optimism), score is actually 1
            # But our response options are already:
            # False=0 (not hopeless), True=1 (hopeless) — for reverse items, these are WRONG.
            # Actually, for the BHS scale: reverse items are the HOPEFUL statements (not hopeless).
            # False=0, True=1 are the values in our schema.
            # For reverse items: False means they DO NOT have hope = 1 point for hopelessness.
            # True means they have hope = 0 points for hopelessness.
            # So: score = 1 - raw_value
            score = 1 - raw_value
        else:
            score = raw_value

        total += score
        max_possible += max(valid_values)
        scored_responses[item_id] = raw_value

    # Find cut-point band
    cut_points = fw.get("cut_points", [])
    band = "Unknown"
    for cp in cut_points:
        if cp["min"] <= total <= cp["max"]:
            band = cp["label"]
            break

    return {
        "framework_id": framework_id,
        "total": total,
        "band": band,
        "item_count": len(items),
        "max_score": max_possible,
        "responses": scored_responses,
    }
