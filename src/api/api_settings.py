from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api.api_dependencies import get_current_user
from src.engine.feature_gate import get_feature_flags, get_tier_label
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


class TestConnectionRequest(BaseModel):
    provider: str  # "ollama" | "gemini" | "anthropic" | "openai" | "opencode_go" | "opencode_zen"
    api_key: str = ""


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]


def _test_gemini(api_key: str) -> dict:
    """Test a Gemini API key and return available models."""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        # Filter for generateContent models and extract IDs
        model_ids = []
        for m in models:
            try:
                if hasattr(m, 'supported_actions') and 'generateContent' in str(m.supported_actions):
                    model_ids.append(m.name.replace("models/", ""))
            except Exception:
                model_ids.append(str(m.name).replace("models/", ""))
        if not model_ids:
            return {"success": False, "error": "No generative models were returned by the Gemini API."}
        return {"success": True, "models": sorted(set(model_ids))}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_anthropic(api_key: str) -> dict:
    """Test an Anthropic API key and return available models."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        models = client.models.list()
        model_ids = [m.id for m in models.data] if hasattr(models, 'data') else []
        if not model_ids:
            return {"success": False, "error": "No models were returned by the Anthropic API."}
        return {"success": True, "models": model_ids}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _test_openai(api_key: str, base_url: str | None = None) -> dict:
    """Test an OpenAI (or OpenAI-compatible) API key and return available models."""
    try:
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.OpenAI(**kwargs)
        models = client.models.list()
        model_ids = [m.id for m in models.data] if hasattr(models, 'data') else [m.id for m in models]
        if not model_ids:
            return {"success": False, "error": "No models were returned by the API."}
        return {"success": True, "models": model_ids[:200]}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/test-connection")
def test_connection(req: TestConnectionRequest, current_user: dict = Depends(get_current_user)):
    """Test an API key for a given provider and return available models."""
    if req.provider == "ollama":
        try:
            models = ollama_client.get_installed_models()
            if models:
                return {"success": True, "models": models}
            return {"success": False, "error": "Ollama is running but no models installed. Run `ollama pull llama3`."}
        except Exception as e:
            return {"success": False, "error": f"Ollama not reachable: {e}"}
    elif req.provider == "gemini":
        if not req.api_key:
            return {"success": False, "error": "API key is required"}
        return _test_gemini(req.api_key)
    elif req.provider == "anthropic":
        if not req.api_key:
            return {"success": False, "error": "API key is required"}
        return _test_anthropic(req.api_key)
    elif req.provider in ("openai", "opencode_go", "opencode_zen"):
        if not req.api_key and req.provider != "ollama":
            return {"success": False, "error": "API key is required"}
        base_urls = {
            "openai": None,
            "opencode_go": config.OPENGODE_GO_BASE_URL,
            "opencode_zen": config.OPENGODE_ZEN_BASE_URL,
        }
        return _test_openai(req.api_key, base_urls.get(req.provider))
    else:
        return {"success": False, "error": f"Unknown provider: {req.provider}"}

@router.get("")
def get_settings(current_user: dict = Depends(get_current_user)):
    try:
        # Pings Ollama and gets installed models
        installed_models = []
        try:
            installed_models = ollama_client.get_installed_models()
        except Exception as e:
            logger.warning(f"Failed to fetch installed Ollama models: {e}")

        # Get active settings from settings_manager
        settings = settings_manager.settings.copy()

        return {
            "settings": settings,
            "installed_ollama_models": installed_models,
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def update_settings(req: SettingsUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Update settings manager (this also syncs to config and persists)
        for key, val in req.settings.items():
            settings_manager.set_setting(key, val)

        return {"status": "success", "settings": settings_manager.settings}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features")
def get_features(current_user: dict = Depends(get_current_user)):
    """Return feature flags and current tier information."""
    return {
        "tier": get_tier_label(),
        "features": get_feature_flags(),
    }
