"""Tests for clinical questionnaire scoring."""

import pytest
from src.assessment.frameworks import get_framework
from src.assessment.scorers import score_questionnaire


def test_phq9_minimal():
    r = score_questionnaire("phq9", {"q1": 0, "q2": 0, "q3": 0, "q4": 0, "q5": 0, "q6": 0, "q7": 0, "q8": 0, "q9": 0})
    assert r["total"] == 0
    assert r["band"] == "Minimal"


def test_phq9_severe():
    r = score_questionnaire("phq9", {"q1": 3, "q2": 3, "q3": 3, "q4": 3, "q5": 3, "q6": 3, "q7": 3, "q8": 3, "q9": 3})
    assert r["total"] == 27
    assert r["band"] == "Severe"


def test_phq9_moderate():
    r = score_questionnaire("phq9", {"q1": 1, "q2": 2, "q3": 1, "q4": 2, "q5": 1, "q6": 1, "q7": 0, "q8": 2, "q9": 0})
    assert 10 <= r["total"] <= 14
    assert r["band"] == "Moderate"


def test_gad7_minimal():
    r = score_questionnaire("gad7", {"q1": 0, "q2": 0, "q3": 0, "q4": 0, "q5": 0, "q6": 0, "q7": 0})
    assert r["total"] == 0
    assert r["band"] == "Minimal"


def test_gad7_severe():
    r = score_questionnaire("gad7", {"q1": 3, "q2": 3, "q3": 3, "q4": 3, "q5": 3, "q6": 3, "q7": 3})
    assert r["total"] == 21
    assert r["band"] == "Severe"


def test_bhs_all_false():
    """All False = 0 on non-reverse (9 items) + 1 on reverse (11 items) = 11."""
    r = score_questionnaire("bhs", {f"q{i}": 0 for i in range(1, 21)})
    assert r["total"] == 11
    assert r["band"] == "Moderate"


def test_bhs_all_true():
    """All True = many hopelessness indicators. Reverse items contribute."""
    r = score_questionnaire("bhs", {f"q{i}": 1 for i in range(1, 21)})
    # Non-reverse items (1,3,5,6,8,10,13,15,19): True=1 → contributes 1 each = 9
    # Reverse items (2,4,7,9,11,12,14,16,17,18,20): True=1 → reverse: score=0
    # Total = 9
    assert r["total"] == 9
    assert r["band"] == "Moderate"


def test_bhs_mixed():
    """Mixed responses should produce a moderate score."""
    responses = {}
    for i in range(1, 21):
        responses[f"q{i}"] = 0  # All False first
    # Set some reverse items to True
    responses["q2"] = 1  # reverse item: True=1 → reverse: 1-1=0
    responses["q7"] = 1  # reverse item: True=1 → reverse: 1-1=0
    responses["q11"] = 1  # reverse item: True=1 → reverse: 1-1=0
    r = score_questionnaire("bhs", responses)
    # 3 reverse items as True: 0 each = 0
    # 8 reverse items as False: 1 each = 8
    # 9 non-reverse items as False: 0 each = 0
    assert r["total"] == 8


def test_framework_has_questionnaire_type():
    for fw_id in ["phq9", "gad7", "bhs"]:
        fw = get_framework(fw_id)
        assert fw is not None
        assert fw["kind"] == "questionnaire"
        assert len(fw["items"]) >= 7


def test_missing_response_raises():
    with pytest.raises(ValueError, match="Missing response"):
        score_questionnaire("phq9", {"q1": 0})


def test_invalid_value_raises():
    with pytest.raises(ValueError, match="Invalid value"):
        score_questionnaire("phq9", {"q1": 0, "q2": 1, "q3": 2, "q4": 0, "q5": 1, "q6": 1, "q7": 0, "q8": 2, "q9": 99})
