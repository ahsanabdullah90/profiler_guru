from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from src.utils.config import config
from src.utils.logger import logger
from src.utils.ollama_client import ollama_client
from src.engine.settings_manager import settings_manager

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

class SettingsUpdateRequest(BaseModel):
    settings: Dict[str, Any]

@router.get("")
def get_settings():
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
        
        # Add env vars/config values that might be useful
        return {
            "settings": settings,
            "installed_ollama_models": installed_models,
            "best_local_model": best_model,
            "has_google_key": bool(config.GOOGLE_API_KEY or config.CLOUD_API_KEY),
            "has_instagram_password": bool(config.INSTAGRAM_PASSWORD)
        }
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("")
def update_settings(req: SettingsUpdateRequest):
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
