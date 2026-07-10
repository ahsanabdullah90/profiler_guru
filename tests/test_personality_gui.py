import os
import json
import shutil
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch

from src.utils.config import config
from src.engine.settings_manager import settings_manager, DEFAULT_SETTINGS
from src.engine.llm_dispatcher import llm_dispatcher
from src.engine.rag_engine import rag_engine
from src.engine.report_generator import report_generator, analyze_monthly_data, generate_charts

@pytest.fixture
def temp_exports_dir(tmp_path):
    """Fixture to temporarily point config.EXPORTS_DIR to a temp path."""
    old_exports = config.EXPORTS_DIR
    old_settings = config.SETTINGS_PATH
    
    temp_dir = tmp_path / "exports"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config.EXPORTS_DIR = temp_dir
    config.SETTINGS_PATH = temp_dir / "settings.json"
    
    # Re-initialize settings manager with new paths
    settings_manager.settings_path = config.SETTINGS_PATH
    settings_manager.reset_to_defaults()
    
    yield temp_dir
    
    config.EXPORTS_DIR = old_exports
    config.SETTINGS_PATH = old_settings
    settings_manager.settings_path = old_settings
    settings_manager.load()

@pytest.fixture
def temp_chats_dir(tmp_path):
    """Fixture to temporarily point config.CHATS_DIR to a temp path and set up mock logs."""
    old_chats = config.CHATS_DIR
    temp_dir = tmp_path / "chats"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config.CHATS_DIR = temp_dir
    
    # Create mock chat logs for "test_contact"
    contact_dir = temp_dir / "test_contact" / "Chats"
    contact_dir.mkdir(parents=True, exist_ok=True)
    
    # Month 1: 2026_04.md
    with open(contact_dir / "2026_04.md", "w", encoding="utf-8") as f:
        f.write("### [2026-04-10 12:00:00] test_contact\nHello. This is an awesome positive day! haha\n---\n")
        
    # Month 2: 2026_05.md
    with open(contact_dir / "2026_05.md", "w", encoding="utf-8") as f:
        f.write("### [2026-05-12 14:00:00] test_contact\nI am so sorry and sad. Very bad news.\n---\n")
        
    # Month 3: 2026_06.md
    with open(contact_dir / "2026_06.md", "w", encoding="utf-8") as f:
        f.write("### [2026-06-15 16:00:00] test_contact\nZabardast, acha sahi shukriya!\n---\n")
        
    yield temp_dir
    
    config.CHATS_DIR = old_chats

# =====================================================================
# 1. Settings Manager Tests
# =====================================================================
def test_settings_persistence(temp_exports_dir):
    # Verify defaults
    assert settings_manager.get_setting("cloud_provider") == "gemini"
    assert settings_manager.get_setting("deep_scan_default") is False
    
    # Change a setting and verify persistence
    settings_manager.set_setting("deep_scan_default", True)
    assert settings_manager.get_setting("deep_scan_default") is True
    assert config.DEEP_SCAN_DEFAULT is True
    
    # Re-load from file to confirm it saved
    settings_manager.load()
    assert settings_manager.get_setting("deep_scan_default") is True
    
    # Reset to defaults
    settings_manager.reset_to_defaults()
    assert settings_manager.get_setting("deep_scan_default") is False
    assert config.DEEP_SCAN_DEFAULT is False

# =====================================================================
# 2. LLM Dispatcher Tests
# =====================================================================
def test_llm_dispatcher_local_routing():
    # Token count fits within local threshold
    prompt = "Simple question"
    token_budget = 1000
    
    with patch('src.engine.llm_dispatcher.ollama_client.generate') as mock_ollama:
        mock_ollama.return_value = "Ollama response"
        
        res = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=token_budget,
            force_cloud=False,
            provider="ollama",
            user_consent=False
        )
        assert res == "Ollama response"
        mock_ollama.assert_called_once()

def test_llm_dispatcher_cloud_routing_with_consent():
    # Large budget triggers cloud routing
    prompt = "Large context..."
    token_budget = 70000  # > 64,000 threshold
    
    # Mock GenAI Client generate_content
    with patch('google.genai.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = MagicMock(text="Gemini response")
        mock_client_class.return_value = mock_client
        
        # Inject API key and model temporarily
        old_key = config.CLOUD_API_KEY
        old_model = config.GEMINI_MODEL
        config.CLOUD_API_KEY = "dummy_api_key"
        config.GEMINI_MODEL = "gemini-1.5-flash"
        config.ENABLE_CLOUD_AI = True
        
        res = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=token_budget,
            force_cloud=False,
            provider="gemini",
            user_consent=True
        )
        assert res == "Gemini response"
        
        config.CLOUD_API_KEY = old_key
        config.GEMINI_MODEL = old_model

def test_llm_dispatcher_missing_key_fallback():
    # Force cloud but missing API key should raise LLMDispatchError
    from src.engine.llm_dispatcher import LLMDispatchError
    old_key = config.CLOUD_API_KEY
    old_gemini_key = config.GOOGLE_API_KEY
    config.CLOUD_API_KEY = ""
    config.GOOGLE_API_KEY = ""
    
    with pytest.raises(LLMDispatchError) as excinfo:
        llm_dispatcher.dispatch(
            prompt="Test",
            token_budget=1000,
            force_cloud=True,
            provider="gemini",
            user_consent=True
        )
    assert "not configured" in str(excinfo.value).lower()
    config.CLOUD_API_KEY = old_key
    config.GOOGLE_API_KEY = old_gemini_key

# =====================================================================
# 3. Fetch Markdown Snippets Tests
# =====================================================================
def test_fetch_markdown_snippets_date_filtering(temp_chats_dir):
    # Fetch all snippets
    all_snippets = rag_engine.fetch_markdown_snippets("test_contact")
    assert "positive" in all_snippets
    assert "sad" in all_snippets
    assert "Zabardast" in all_snippets
    
    # Filter: 2026_05 to 2026_06 (inclusive)
    filtered = rag_engine.fetch_markdown_snippets("test_contact", start_month="2026_05", end_month="2026_06")
    assert "positive" not in filtered  # 2026_04 should be excluded
    assert "sad" in filtered
    assert "Zabardast" in filtered
    
    # Filter: Single month 2026_04
    single = rag_engine.fetch_markdown_snippets("test_contact", start_month="2026_04", end_month="2026_04")
    assert "positive" in single
    assert "sad" not in single
    assert "Zabardast" not in single

# =====================================================================
# 4. Report Generator Tests
# =====================================================================
def test_monthly_metrics_analysis(temp_chats_dir):
    months, counts, sentiments = analyze_monthly_data("test_contact")
    assert len(months) == 3
    assert months == ["2026-04", "2026-05", "2026-06"]
    assert counts == [1, 1, 1]
    
    # Check sentiment score heuristics
    assert sentiments[0] > 0.0   # Positive (awesome, happy, haha)
    assert sentiments[1] < 0.0   # Negative (sorry, sad, bad)
    assert sentiments[2] > 0.0   # Positive Urdu (Zabardast, acha, shukriya)

def test_pdf_generation(temp_exports_dir, temp_chats_dir):
    pdf_path = temp_exports_dir / "test_report.pdf"
    
    settings = {
        "pdf_include_textual_profile": True,
        "pdf_include_charts": True,
        "pdf_include_raw_snippets": True,
        "report_sections_order": ["textual_profile", "charts", "snippets"]
    }
    
    content = "## Psychological Profile\nSubject displays premium agentic behaviors."
    
    report_generator.create_assessment_pdf(
        contact="test_contact",
        start_month="2026_04",
        end_month="2026_06",
        content=content,
        settings=settings,
        out_path=pdf_path
    )
    
    # Assert PDF file was created and is not empty
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 1000


# =====================================================================
# 5. Fallback Negation and Assessment Density Validation
# =====================================================================
def test_negation_sentiment_fallback(temp_chats_dir):
    contact_dir = config.CHATS_DIR / "test_contact" / "Chats"
    with open(contact_dir / "2026_07.md", "w", encoding="utf-8") as f:
        f.write("### [2026-07-10 12:00:00] test_contact\nI am not happy. This is not good. I do not love this.\n---\n")

    months, counts, sentiments = analyze_monthly_data("test_contact", start_month="2026_07", end_month="2026_07")
    assert len(sentiments) == 1
    assert sentiments[0] <= 0.0

def test_assessment_block_density_verification(temp_chats_dir):
    config.ASSESSMENT_MIN_BLOCKS = 5
    from fastapi.testclient import TestClient
    from main_api import app
    from src.api.api_dependencies import get_current_user, create_jwt_token
    
    # We must patch the dependency to return dummy auth
    app.dependency_overrides[get_current_user] = lambda: {"sub": "portal"}
    
    client = TestClient(app)
    token = create_jwt_token()
    try:
        response = client.post(
            "/api/v1/rag/contacts/test_contact/profile",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "start_month": "2026_04",
                "end_month": "2026_06",
                "force_cloud": False,
                "user_consent": True
            }
        )
        assert response.status_code == 400
        assert "density is insufficient" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()

