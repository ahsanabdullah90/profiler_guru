"""Tests for model size classification and cloud detection."""

from src.assessment.model_size import classify_model, is_cloud_model


def test_is_cloud_model_gpt4o():
    assert is_cloud_model("gpt-4o:latest") is True


def test_is_cloud_model_claude():
    assert is_cloud_model("claude-3-opus:latest") is True


def test_is_cloud_model_gemini_pro():
    assert is_cloud_model("gemini-1.5-pro") is True


def test_is_cloud_model_gemini_flash():
    assert is_cloud_model("gemini-2.0-flash") is True


def test_is_cloud_model_o1():
    assert is_cloud_model("o1-preview") is True


def test_is_cloud_model_o3():
    assert is_cloud_model("o3-mini") is True


def test_is_not_cloud_local():
    assert is_cloud_model("llama3:8b") is False


def test_is_not_cloud_mistral():
    assert is_cloud_model("mistral:7b") is False


def test_is_not_cloud_empty():
    assert is_cloud_model("") is False


def test_is_not_cloud_unknown():
    assert is_cloud_model("my-custom-model") is False


def test_classify_large_gpt4():
    assert classify_model("gpt-4-32k") == "large"


def test_classify_large_claude3():
    assert classify_model("claude-3-opus") == "large"


def test_classify_large_llama70b():
    assert classify_model("llama3:70b") == "large"


def test_classify_large_mixtral_large():
    assert classify_model("mixtral:8x22b") == "large"


def test_classify_large_gemini_pro():
    assert classify_model("gemini-1.5-pro") == "large"


def test_classify_medium_llama8b():
    assert classify_model("llama3.1:8b") == "medium"


def test_classify_medium_mistral_nemo():
    assert classify_model("mistral-nemo") == "medium"


def test_classify_medium_mixtral_8x7b():
    assert classify_model("mixtral:8x7b") == "medium"


def test_classify_medium_qwen_14b():
    assert classify_model("qwen2.5:14b") == "medium"


def test_classify_medium_phi3_14b():
    assert classify_model("phi3:14b") == "medium"


def test_classify_small_phi3_mini():
    assert classify_model("phi3:mini") == "small"


def test_classify_small_unknown():
    assert classify_model("tiny-llama:1b") == "small"


def test_classify_small_empty():
    assert classify_model("") == "small"
