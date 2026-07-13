"""Tests for assessment framework definitions, prompt templates, KB queries, and output parsing."""


from src.assessment.frameworks import (
    DEFAULT_FRAMEWORK,
    FRAMEWORKS,
    get_dimension_ids,
    get_framework,
)
from src.assessment.kb_queries import get_kb_query
from src.assessment.output_parser import (
    parse_assessment_output,
    parse_classification,
    parse_scores,
    strip_score_blocks,
)
import pytest
from src.assessment.prompt_templates import get_prompt


def test_framework_count():
    assert len(FRAMEWORKS) == 7  # 4 trait + 3 clinical


def test_all_frameworks_have_required_fields():
    for fw_id, fw in FRAMEWORKS.items():
        assert fw["id"] == fw_id
        assert fw["label"]
        assert fw["description"]
        if fw.get("kind") == "questionnaire":
            assert fw.get("scoring") == "sum"
            assert len(fw.get("items", [])) >= 7
            assert fw.get("cut_points")
            assert len(fw["cut_points"]) >= 3
        else:
            assert len(fw.get("dimensions", [])) >= 3
            assert fw.get("chart_type") in ("bars", "radar", "classification")
            assert fw.get("kb_query")


def test_default_framework_exists():
    assert DEFAULT_FRAMEWORK in FRAMEWORKS


def test_all_frameworks_have_prompts():
    for fw_id in FRAMEWORKS:
        fw = FRAMEWORKS[fw_id]
        if fw.get("kind") == "questionnaire":
            continue  # questionnaires are scored deterministically, no prompts needed
        p = get_prompt(fw_id)
        assert p is not None, f"Missing prompts for {fw_id}"
        assert p["system"], f"Empty system prompt for {fw_id}"
        assert p["user"], f"Empty user prompt for {fw_id}"
        assert "{sender_ctx}" in p["system"], f"Missing sender_ctx in system prompt for {fw_id}"
        assert "{name}" in p["user"], f"Missing name in user prompt for {fw_id}"
        assert "{markdown_snippets}" in p["user"], f"Missing markdown_snippets in user prompt for {fw_id}"


def test_all_frameworks_have_kb_queries():
    for fw_id in FRAMEWORKS:
        fw = FRAMEWORKS[fw_id]
        if fw.get("kind") == "questionnaire":
            continue  # questionnaires don't use KB
        q = get_kb_query(fw_id)
        assert q, f"Empty KB query for {fw_id}"
        assert len(q) > 10


def test_get_framework_unknown():
    assert get_framework("nonexistent") is None


def test_get_dimension_ids():
    ids = get_dimension_ids("big_five")
    assert ids == ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


def test_get_dimension_ids_unknown():
    assert get_dimension_ids("nonexistent") == []


def test_parse_scores_valid():
    md = "<!-- SCORES: {\"openness\": 7, \"extraversion\": 5} -->\nNarrative text"
    scores = parse_scores(md)
    assert scores == {"openness": 7, "extraversion": 5}


def test_parse_scores_no_block():
    md = "Just narrative text without scores"
    scores = parse_scores(md)
    assert scores is None


def test_parse_scores_invalid_json():
    md = "<!-- SCORES: {bad} -->\nNarrative"
    scores = parse_scores(md)
    assert scores is None


def test_parse_classification_valid():
    md = "<!-- CLASSIFICATION: Secure -->\nNarrative"
    cls = parse_classification(md)
    assert cls == "Secure"


def test_parse_classification_none():
    md = "Just narrative"
    cls = parse_classification(md)
    assert cls is None


def test_strip_score_blocks():
    md = "<!-- SCORES: {\"x\": 1} -->\n<!-- CLASSIFICATION: A -->\nNarrative"
    stripped = strip_score_blocks(md)
    assert stripped == "Narrative"


def test_parse_assessment_output_big_five():
    md = "<!-- SCORES: {\"openness\": 8} -->\n# Analysis\nDetailed text."
    result = parse_assessment_output(md, "big_five")
    assert result["scores"] == {"openness": 8}
    assert result["classification"] is None
    assert result["narrative"] == "# Analysis\nDetailed text."


def test_parse_assessment_output_attachment():
    md = "<!-- SCORES: {\"secure\": 5, \"anxious\": 8} -->\n<!-- CLASSIFICATION: Anxious -->\n# Analysis"
    result = parse_assessment_output(md, "attachment")
    assert result["scores"] == {"secure": 5, "anxious": 8}
    assert result["classification"] == "Anxious"
    assert result["narrative"] == "# Analysis"


def test_framework_dimension_count():
    assert len(get_dimension_ids("communication_style")) == 5
    assert len(get_dimension_ids("big_five")) == 5
    assert len(get_dimension_ids("attachment")) == 4
    assert len(get_dimension_ids("emotional_intelligence")) == 5


def test_system_prompt_formatting():
    from src.assessment.pipeline import _SENDER_CTX_FMT

    ctx = _SENDER_CTX_FMT.format(insta_user="testuser")
    assert "testuser" in ctx
    assert "your own messages" in ctx


def test_all_frameworks_have_modular_steps():
    from src.assessment.modular_steps import get_modular_steps

    for fw_id in FRAMEWORKS:
        fw = FRAMEWORKS[fw_id]
        if fw.get("kind") == "questionnaire":
            continue  # questionnaires don't use modular steps
        steps = get_modular_steps(fw_id)
        assert steps is not None, f"Missing modular steps for {fw_id}"
        assert len(steps) >= 4, f"Too few steps for {fw_id}: {len(steps)}"
        for idx, step in enumerate(steps):
            assert step["id"]
            assert step["label"]
            assert step["system"]
            assert step["user"]
            assert step["output_key"]
            if step.get("needs_logs", True):
                assert "{chat_logs}" in step["user"], f"Missing {{chat_logs}} in {fw_id} step {step['id']}"
            if idx > 0:
                assert "{context}" in step["user"], f"Missing {{context}} in {fw_id} step {step['id']} (idx={idx})"


def test_modular_step_count():
    from src.assessment.modular_steps import get_modular_steps

    assert len(get_modular_steps("communication_style")) == 5
    assert len(get_modular_steps("big_five")) == 5
    assert len(get_modular_steps("attachment")) == 6
    assert len(get_modular_steps("emotional_intelligence")) == 8


def test_modular_final_step_is_synthesis():
    from src.assessment.modular_steps import get_modular_steps

    for fw_id in FRAMEWORKS:
        fw = FRAMEWORKS[fw_id]
        if fw.get("kind") == "questionnaire":
            continue
        steps = get_modular_steps(fw_id)
        last = steps[-1]
        assert last["id"] == "synthesis"
        assert last["output_key"] == "final"
        assert last.get("needs_logs", True) is False


def test_truncate_to_chars():
    from src.assessment.pipeline import _truncate_to_chars

    text = "Block 1\n---\nBlock 2\n---\nBlock 3\n---\nBlock 4"
    truncated = _truncate_to_chars(text, 15)
    assert "truncated" in truncated
    # Original text before the second block should be preserved
    assert text.startswith("Block 1")


def test_truncate_to_chars_no_marker():
    from src.assessment.pipeline import _truncate_to_chars

    text = "A" * 100
    truncated = _truncate_to_chars(text, 50)
    assert "truncated" in truncated
    assert len(truncated) >= 50


def test_truncate_to_chars_no_truncation():
    from src.assessment.pipeline import _truncate_to_chars

    text = "Short text"
    assert _truncate_to_chars(text, 100) == text


def test_assessment_routing_to_single_pass():
    """Large model should use single-pass pipeline."""
    from unittest.mock import patch

    from src.assessment.pipeline import run_assessment

    with patch("src.assessment.pipeline._run_single_pass", return_value={"pipeline_mode": "single", "scores": {}}):
        result = run_assessment(
            name="test",
            framework_id="big_five",
            markdown_snippets="data",
            total_messages=10,
            token_estimate=1000,
            start_month="2026_01",
            end_month="2026_06",
            model_name="gpt-4o",
        )
        assert result["pipeline_mode"] == "single"


def test_assessment_routing_to_modular():
    """Small model should use modular pipeline."""
    from unittest.mock import patch

    from src.assessment.pipeline import run_assessment

    with patch("src.assessment.pipeline.run_assessment_modular", return_value={"pipeline_mode": "modular", "total_steps": 5}):
        result = run_assessment(
            name="test",
            framework_id="big_five",
            markdown_snippets="data",
            total_messages=10,
            token_estimate=1000,
            start_month="2026_01",
            end_month="2026_06",
            model_name="llama3:8b",
        )
        assert result["pipeline_mode"] == "modular"


def test_gemma3_classified_as_large():
    """gemma3:4b should use single-pass pipeline."""
    from src.assessment.model_size import classify_model

    assert classify_model("gemma3:4b") == "large"
    assert classify_model("gemma3:12b") == "large"


def test_empty_llm_output_raises_in_single_pass():
    """Empty LLM output should raise ValueError in single-pass pipeline."""
    from unittest.mock import patch, MagicMock
    from src.assessment.pipeline import _run_single_pass
    from src.engine.llm_dispatcher import LLMDispatcher

    fw = {
        "label": "Big Five",
        "dimensions": [
            {"id": "openness", "label": "Openness", "description": "Test"}
        ],
    }

    with patch("src.assessment.pipeline._retrieve_kb", return_value=("", [])):
        with patch("src.assessment.pipeline.get_prompt", return_value={
            "system": "System {sender_ctx}",
            "user": "User {name} {markdown_snippets} {dimension_list} {start_month} {end_month} {total_messages} {kb_context} {sender_ctx} {dimension_instructions}",
        }):
            with patch.object(LLMDispatcher, "dispatch", return_value=""):
                with pytest.raises(ValueError, match="empty response"):
                    _run_single_pass(
                        name="test",
                        framework_id="big_five",
                        fw=fw,
                        markdown_snippets="data",
                        total_messages=10,
                        token_estimate=1000,
                        start_month="2026_01",
                        end_month="2026_06",
                    )


def test_empty_llm_output_raises_in_modular():
    """Empty LLM step output should raise ValueError in modular pipeline."""
    from unittest.mock import patch
    from src.assessment.pipeline import run_assessment_modular
    from src.engine.llm_dispatcher import LLMDispatcher

    with patch("src.assessment.pipeline.get_modular_steps", return_value=[
        {
            "id": "step1",
            "label": "Test Step",
            "needs_logs": True,
            "system": "System",
            "user": "User {chat_logs} {context} {name} {total_messages} {start_month} {end_month}",
            "output_key": "step1",
        },
    ]):
        with patch.object(LLMDispatcher, "dispatch", return_value=""):
            with pytest.raises(ValueError, match="empty output"):
                run_assessment_modular(
                    name="test",
                    framework_id="big_five",
                    markdown_snippets="data",
                    total_messages=10,
                    token_estimate=1000,
                    start_month="2026_01",
                    end_month="2026_06",
                    model_size="small",
                )
