"""Unified model aggregation endpoint — lists available models from all configured providers."""

import time

from fastapi import APIRouter, Depends
from src.api.api_dependencies import get_current_user
from src.assessment.model_size import is_cloud_model
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.ollama_client import ollama_client

router = APIRouter(prefix="/api/v1/models", tags=["Models"])

_cache: dict[str, tuple[float, list[dict] | None, str | None]] = {}
CACHE_TTL = 120


def _try_provider_fetch(prompt: str) -> list[dict]:
    """To be implemented per provider below."""


def _try_ollama() -> tuple[list[dict], str | None]:
    try:
        models = ollama_client.get_installed_models()
        if models:
            return [
                {"provider": "ollama", "model": m, "label": m, "is_cloud": is_cloud_model(m)}
                for m in models
            ], None
        return [], "Ollama is reachable but no models installed."
    except Exception as e:
        return [], f"Ollama not reachable: {e}"


def _try_gemini() -> tuple[list[dict], str | None]:
    api_key = settings_manager.get_setting("gemini_api_key", "") or config.GOOGLE_API_KEY
    if not api_key:
        return [], "Gemini API key not configured."
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        models = client.models.list()
        model_ids = []
        for m in models:
            try:
                if hasattr(m, "supported_actions") and "generateContent" in str(m.supported_actions):
                    model_ids.append(m.name.replace("models/", ""))
            except Exception:
                try:
                    model_ids.append(str(m.name).replace("models/", ""))
                except Exception:
                    pass
        if not model_ids:
            return [], "No generative models returned by Gemini API."
        return [
            {"provider": "gemini", "model": m, "label": m, "is_cloud": True}
            for m in sorted(set(model_ids))
        ], None
    except Exception as e:
        return [], f"Gemini API error: {e}"


def _try_anthropic() -> tuple[list[dict], str | None]:
    api_key = settings_manager.get_setting("anthropic_api_key", "") or config.ANTHROPIC_API_KEY
    if not api_key:
        return [], "Anthropic API key not configured."
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        models = client.models.list()
        model_ids = [m.id for m in models.data] if hasattr(models, "data") else []
        if not model_ids:
            return [], "No models returned by Anthropic API."
        return [
            {"provider": "anthropic", "model": m, "label": m, "is_cloud": True}
            for m in model_ids
        ], None
    except Exception as e:
        return [], f"Anthropic API error: {e}"


def _try_openai(api_key: str, base_url: str | None, provider_tag: str) -> tuple[list[dict], str | None]:
    if not api_key:
        return [], f"{provider_tag} API key not configured."
    try:
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        client = openai.OpenAI(**kwargs)
        models = client.models.list()
        model_ids = (
            [m.id for m in models.data]
            if hasattr(models, "data")
            else [m.id for m in models]
        )
        if not model_ids:
            return [], f"No models returned by {provider_tag} API."
        return [
            {"provider": provider_tag, "model": m, "label": m, "is_cloud": True}
            for m in model_ids[:200]
        ], None
    except Exception as e:
        return [], f"{provider_tag} API error: {e}"


def _list_ollama_models():
    return _try_ollama()


def _list_gemini_models():
    return _try_gemini()


def _list_anthropic_models():
    return _try_anthropic()


def _list_openai_models():
    key = settings_manager.get_setting("openai_api_key", "") or config.OPENAI_API_KEY
    return _try_openai(key, base_url=None, provider_tag="openai")


def _list_opencode_go_models():
    key = settings_manager.get_setting("opencode_go_api_key", "") or config.OPENGODE_GO_API_KEY
    return _try_openai(key, base_url=config.OPENGODE_GO_BASE_URL, provider_tag="opencode_go")


def _list_opencode_zen_models():
    key = settings_manager.get_setting("opencode_zen_api_key", "") or config.OPENGODE_ZEN_API_KEY
    return _try_openai(key, base_url=config.OPENGODE_ZEN_BASE_URL, provider_tag="opencode_zen")


_PROVIDER_FETCHERS: list[tuple[str, callable]] = [
    ("ollama", _list_ollama_models),
    ("gemini", _list_gemini_models),
    ("anthropic", _list_anthropic_models),
    ("openai", _list_openai_models),
    ("opencode_go", _list_opencode_go_models),
    ("opencode_zen", _list_opencode_zen_models),
]


def _fetch_all_models():
    all_models: list[dict] = []
    errors: dict[str, str] = {}
    now = time.time()

    for provider_name, fetcher in _PROVIDER_FETCHERS:
        cache_key = f"provider:{provider_name}"
        cached = _cache.get(cache_key)
        if cached and (now - cached[0]) < CACHE_TTL:
            models, err = cached[1], cached[2]
        else:
            try:
                models, err = fetcher()
            except Exception as e:
                models, err = [], str(e)
            _cache[cache_key] = (now, models, err)
        if err:
            errors[provider_name] = err
        if models:
            all_models.extend(models)

    return {"models": all_models, "errors": errors, "cached_at": now}


@router.get("")
def list_models(current_user: dict = Depends(get_current_user)):
    return _fetch_all_models()


@router.post("/refresh")
def refresh_model_cache(current_user: dict = Depends(get_current_user)):
    _cache.clear()
    result = _fetch_all_models()
    return {"status": "refreshed", **result}
