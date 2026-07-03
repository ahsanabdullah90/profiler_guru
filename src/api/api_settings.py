from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.api.api_dependencies import get_current_user
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any]

@router.get("")
def get_settings(current_user: dict = Depends(get_current_user)):
    try:
        # Pings Ollama and gets installed models
        installed_models = []
        try:
            installed_models = ollama_client.get_installed_models()
        except Exception as e:
            logger.warning(f"Failed to fetch installed Ollama models: {e}")

        best_model = None
        if installed_models:
            best_model = ollama_client.get_best_model(installed_models)

        # Get active settings from settings_manager
        settings = settings_manager.settings.copy()

        return {
            "settings": settings,
            "installed_ollama_models": installed_models,
            "best_local_model": best_model,
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def update_settings(req: SettingsUpdateRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Update settings manager
        for key, val in req.settings.items():
            settings_manager.set_setting(key, val)

        # Dynamically sync key configs
        if "cloud_provider" in req.settings:
            config.LLM_PROVIDER = req.settings["cloud_provider"]
        if "ollama_model" in req.settings:
            config.OLLAMA_MODEL = req.settings["ollama_model"]
        if "cloud_api_key" in req.settings:
            config.CLOUD_API_KEY = req.settings["cloud_api_key"]
            config.GOOGLE_API_KEY = req.settings["cloud_api_key"]

        return {"status": "success", "settings": settings_manager.settings}
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
