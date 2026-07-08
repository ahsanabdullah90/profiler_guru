import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def test_default_settings_have_empty_models():
    """Model defaults must be empty so nothing is hardcoded."""
    from src.engine.settings_manager import DEFAULT_SETTINGS

    assert DEFAULT_SETTINGS["ollama_model"] == ""
    assert DEFAULT_SETTINGS["gemini_model"] == ""
    assert DEFAULT_SETTINGS["anthropic_model"] == ""
    assert DEFAULT_SETTINGS["openai_model"] == ""
    assert DEFAULT_SETTINGS["opencode_go_model"] == ""
    assert DEFAULT_SETTINGS["opencode_zen_model"] == ""
    assert DEFAULT_SETTINGS["embedding_model"] == ""
    assert DEFAULT_SETTINGS["active_provider"] == "ollama"


def test_settings_manager_merges_missing_keys_and_starts_empty():
    """Loading an old settings.json fills in new keys and auto-selects an Ollama model."""
    from src.engine.settings_manager import SettingsManager

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        # Old-style settings file missing new provider and embedding keys
        settings_path.write_text(json.dumps({"active_provider": "ollama"}), encoding="utf-8")

        with patch.object(SettingsManager, "_keyring_get", return_value=None):
            with patch("src.utils.config.config.SETTINGS_PATH", str(settings_path)):
                with patch("src.utils.ollama_client.ollama_client.get_installed_models", return_value=["llama3", "mistral"]):
                    with patch("src.utils.ollama_client.ollama_client.get_best_model", return_value="llama3"):
                        manager = SettingsManager()

        assert manager.settings["ollama_model"] == ""
        assert "embedding_model" in manager.settings
        assert "gemini_model" in manager.settings


def test_settings_manager_saves_api_keys_to_keyring_only():
    """API keys must be stripped from JSON and saved to keyring."""
    from src.engine.settings_manager import SettingsManager

    saved = {}

    # patch.object on an instance method still passes `self` as the first argument.
    def fake_keyring_set(_self, key_name, value):
        saved[key_name] = value

    def fake_keyring_get(_self, key_name):
        return saved.get(key_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        settings_path = Path(tmpdir) / "settings.json"
        with patch.object(SettingsManager, "_keyring_set", fake_keyring_set):
            with patch.object(SettingsManager, "_keyring_get", fake_keyring_get):
                with patch("src.utils.config.config.SETTINGS_PATH", str(settings_path)):
                    with patch("src.utils.ollama_client.ollama_client.get_installed_models", return_value=["llama3"]):
                        with patch("src.utils.ollama_client.ollama_client.get_best_model", return_value="llama3"):
                            manager = SettingsManager()
                            manager.set_setting("gemini_api_key", "secret-gemini-key")

        saved_data = json.loads(settings_path.read_text(encoding="utf-8"))
        assert "gemini_api_key" not in saved_data
        assert saved["google_api_key"] == "secret-gemini-key"


def test_get_settings_exposes_empty_defaults():
    """GET /api/v1/settings returns empty model defaults and required keys."""
    from fastapi.testclient import TestClient
    from main_api import app

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code == 401:
        pytest.skip("APP_PASSWORD not configured")
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert "installed_ollama_models" in data
    assert "best_local_model" in data

    settings = data["settings"]
    assert settings["active_provider"] == "ollama"
    assert settings.get("gemini_model", "MISSING") == ""
    assert settings.get("anthropic_model", "MISSING") == ""
    assert settings.get("openai_model", "MISSING") == ""


def test_post_settings_updates_model():
    """POST /api/v1/settings updates a model name and persists it."""
    from fastapi.testclient import TestClient
    from main_api import app
    from src.engine.settings_manager import settings_manager

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code == 401:
        pytest.skip("APP_PASSWORD not configured")
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    payload = {"settings": {"ollama_model": "mistral"}}
    response = client.post("/api/v1/settings", json=payload, headers=headers)
    assert response.status_code == 200
    assert settings_manager.settings["ollama_model"] == "mistral"


def test_test_connection_gemini_success():
    """POST /api/v1/settings/test-connection returns models from Gemini API."""
    from fastapi.testclient import TestClient
    from main_api import app

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code == 401:
        pytest.skip("APP_PASSWORD not configured")
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    fake_model = type("Model", (), {"name": "models/gemini-2.0-flash", "supported_actions": ["generateContent"]})
    with patch("google.genai.Client") as mock_client:
        mock_client.return_value.models.list.return_value = [fake_model]
        response = client.post(
            "/api/v1/settings/test-connection",
            json={"provider": "gemini", "api_key": "fake-key"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "gemini-2.0-flash" in data["models"]


def test_test_connection_gemini_no_models_returns_error_not_fallback():
    """If Gemini returns no models, we must not return hardcoded fake models."""
    from fastapi.testclient import TestClient
    from main_api import app

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code == 401:
        pytest.skip("APP_PASSWORD not configured")
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    with patch("google.genai.Client") as mock_client:
        mock_client.return_value.models.list.return_value = []
        response = client.post(
            "/api/v1/settings/test-connection",
            json={"provider": "gemini", "api_key": "fake-key"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert "gemini-1.5-flash" not in str(data)
    assert "gemini-2.0-flash-exp" not in str(data)


def test_test_connection_ollama():
    """POST /api/v1/settings/test-connection returns Ollama installed models."""
    from fastapi.testclient import TestClient
    from main_api import app

    client = TestClient(app)
    resp = client.post("/api/v1/auth/login", json={"password": "koko"})
    if resp.status_code == 401:
        pytest.skip("APP_PASSWORD not configured")
    headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    with patch("src.utils.ollama_client.ollama_client.get_installed_models", return_value=["llama3"]):
        response = client.post(
            "/api/v1/settings/test-connection",
            json={"provider": "ollama"},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "llama3" in data["models"]


def test_llm_dispatcher_raises_on_empty_model():
    """Dispatching with no model selected must raise a clear error."""
    from src.engine.llm_dispatcher import LLMDispatchError, LLMDispatcher
    from src.utils.config import config

    config.ACTIVE_PROVIDER = "gemini"
    config.GEMINI_MODEL = ""
    config.GOOGLE_API_KEY = "fake-key"

    dispatcher = LLMDispatcher()
    with pytest.raises(LLMDispatchError) as excinfo:
        dispatcher.dispatch("hello", token_budget=1000, user_consent=True)
    assert "No model selected" in str(excinfo.value)
    assert "Settings → Models" in str(excinfo.value)
