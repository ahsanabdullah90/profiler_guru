import json
import os
from pathlib import Path

from src.utils.config import config
from src.utils.logger import logger

DEFAULT_SETTINGS = {
    "active_provider": "ollama",
    # Model names are intentionally empty by default and resolved dynamically
    # (auto-selected from installed models or chosen after testing a provider).
    "ollama_model": "",
    "gemini_model": "",
    "anthropic_model": "",
    "openai_model": "",
    "opencode_go_model": "",
    "opencode_zen_model": "",
    "opencode_go_base_url": "https://opencode.ai/zen/go/v1",
    "opencode_zen_base_url": "https://opencode.ai/zen/v1",
    # Embedding configuration
    "embedding_provider": "ollama",
    "embedding_model": "",
    "instagram_username": "",
    "display_name": "",
    # Legacy backward compatibility
    "cloud_api_key": "",
    "cloud_provider": "",
    "llm_provider": "",
    # Existing settings
    "deep_scan_default": False,
    "pdf_include_charts": True,
    "pdf_include_raw_snippets": True,
    "pdf_include_textual_profile": True,
    "report_sections_order": ["textual_profile", "charts", "snippets"],
    "rag_relevancy_threshold": 0.3,
    "rag_token_budget_ollama": 15000,
    "rag_token_budget_gemini": 300000,
    "assessment_min_blocks": 5,
    "prompt_overrides": {},
}

# Map provider names to keyring key names
_KEYRING_MAP = {
    "gemini": "google_api_key",
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
            "opencode_go": "opencode_go_api_key",
            "opencode_zen": "opencode_zen_api_key",
            "instagram": "instagram_username",
}


class SettingsManager:
    def __init__(self):
        self.settings_path = Path(config.SETTINGS_PATH)
        self.settings = {}
        self.load()

    def _keyring_get(self, key_name: str) -> str | None:
        """Read a value from OS keyring."""
        try:
            import keyring
            return keyring.get_password("Profile_Guru", key_name)
        except Exception as e:
            logger.debug(f"Failed to read {key_name} from keyring: {e}")
            return None

    def _keyring_set(self, key_name: str, value: str) -> None:
        """Write a value to OS keyring."""
        if not value:
            return
        try:
            import keyring
            keyring.set_password("Profile_Guru", key_name, value)
        except Exception as e:
            logger.warning(f"Failed to save {key_name} to keyring: {e}")

    def load(self):
        """Loads settings from disk or initializes defaults, fetching secrets from keyring."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, encoding="utf-8") as f:
                    self.settings = json.load(f)
                logger.info(f"Loaded settings from {self.settings_path}")
            except Exception as e:
                logger.error(f"Failed to load settings from {self.settings_path}: {e}")
                self.settings = dict(DEFAULT_SETTINGS)
        else:
            self.settings = dict(DEFAULT_SETTINGS)

        # Merge any new default keys (handles upgrades from older settings.json files)
        for key, default_val in DEFAULT_SETTINGS.items():
            if key not in self.settings:
                self.settings[key] = default_val

        # Load provider API keys from keyring, falling back to config (env)
        provider_key_map = {
            "gemini": ("google_api_key", config.GOOGLE_API_KEY or config.CLOUD_API_KEY),
            "anthropic": ("anthropic_api_key", config.ANTHROPIC_API_KEY),
            "openai": ("openai_api_key", config.OPENAI_API_KEY),
            "opencode_go": ("opencode_go_api_key", config.OPENGODE_GO_API_KEY),
            "opencode_zen": ("opencode_zen_api_key", config.OPENGODE_ZEN_API_KEY),
        }

        for _provider, (key_name, fallback) in provider_key_map.items():
            val = self._keyring_get(key_name) or fallback
            if val:
                self.settings[f"{_provider}_api_key"] = val
                # Save to keyring if we got it from env but not yet in keyring
                if not self._keyring_get(key_name):
                    self._keyring_set(key_name, val)

        # Load instagram_username from keyring, falling back to config (env)
        insta_val = self._keyring_get("instagram_username") or config.INSTAGRAM_USERNAME
        if insta_val:
            self.settings["instagram_username"] = insta_val
            # Save to keyring if we got it from env but not yet in keyring
            if not self._keyring_get("instagram_username"):
                self._keyring_set("instagram_username", insta_val)

        self._apply_to_config()

    def save(self):
        """Saves current settings to disk, keeping sensitive keys in keyring only."""
        try:
            os.makedirs(self.settings_path.parent, exist_ok=True)
            serializable_settings = dict(self.settings)

            # Strip sensitive keys before saving to JSON, keeping them in the keyring
            _SETTING_TO_KEYRING = {
                "gemini_api_key": "google_api_key",
                "anthropic_api_key": "anthropic_api_key",
                "openai_api_key": "openai_api_key",
                "opencode_go_api_key": "opencode_go_api_key",
                "opencode_zen_api_key": "opencode_zen_api_key",
                "cloud_api_key": "google_api_key",  # legacy cloud key maps to Gemini
                "instagram_username": "instagram_username",
            }
            for key in list(serializable_settings.keys()):
                keyring_name = _SETTING_TO_KEYRING.get(key)
                if keyring_name is not None:
                    val = serializable_settings.pop(key)
                    if val:
                        self._keyring_set(keyring_name, val)

            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(serializable_settings, f, indent=4)
            logger.info(f"Saved settings to {self.settings_path} (sensitive keys stripped)")
        except Exception as e:
            logger.error(f"Failed to save settings to {self.settings_path}: {e}")

    def get_setting(self, key, default=None):
        """Retrieves a single setting value, falling back to default if not present."""
        if key not in self.settings:
            val = DEFAULT_SETTINGS.get(key, default)
            self.settings[key] = val
            return val
        return self.settings[key]

    def set_setting(self, key, value):
        """Sets a setting value and saves the changes."""
        self.settings[key] = value
        self.save()
        self._apply_to_config()

    def reset_to_defaults(self):
        """Resets all settings to default values and saves them."""
        self.settings = dict(DEFAULT_SETTINGS)
        if os.getenv("CLOUD_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            self.settings["gemini_api_key"] = os.getenv("CLOUD_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.save()
        self._apply_to_config()

    def _apply_to_config(self):
        """Applies relevant settings back to the global Config object so they take effect immediately."""
        config.ACTIVE_PROVIDER = self.settings.get("active_provider", "ollama")
        config.LLM_PROVIDER = self.settings.get("llm_provider", "ollama")
        config.OLLAMA_MODEL = self.settings.get("ollama_model", "")
        config.CLOUD_PROVIDER = self.settings.get("cloud_provider", "")
        gemini_key = self.settings.get("gemini_api_key", "")
        legacy_cloud_key = self.settings.get("cloud_api_key", "")
        config.GOOGLE_API_KEY = gemini_key or legacy_cloud_key
        config.CLOUD_API_KEY = gemini_key or legacy_cloud_key
        config.ANTHROPIC_API_KEY = self.settings.get("anthropic_api_key", "")
        config.OPENAI_API_KEY = self.settings.get("openai_api_key", "")
        config.OPENGODE_GO_API_KEY = self.settings.get("opencode_go_api_key", "")
        config.OPENGODE_ZEN_API_KEY = self.settings.get("opencode_zen_api_key", "")
        config.GEMINI_MODEL = self.settings.get("gemini_model", "")
        config.ANTHROPIC_MODEL = self.settings.get("anthropic_model", "")
        config.OPENAI_MODEL = self.settings.get("openai_model", "")
        config.OPENGODE_GO_MODEL = self.settings.get("opencode_go_model", "")
        config.OPENGODE_ZEN_MODEL = self.settings.get("opencode_zen_model", "")
        config.EMBEDDING_PROVIDER = self.settings.get("embedding_provider", "ollama")
        config.EMBEDDING_MODEL = self.settings.get("embedding_model", "")
        config.DEEP_SCAN_DEFAULT = self.settings.get("deep_scan_default", False)
        config.PDF_INCLUDE_CHARTS = self.settings.get("pdf_include_charts", True)
        config.PDF_INCLUDE_RAW_SNIPPETS = self.settings.get("pdf_include_raw_snippets", True)
        config.PDF_INCLUDE_TEXTUAL_PROFILE = self.settings.get("pdf_include_textual_profile", True)
        config.RAG_RELEVANCY_THRESHOLD = float(self.settings.get("rag_relevancy_threshold", 0.3))
        config.RAG_TOKEN_BUDGET_OLLAMA = int(self.settings.get("rag_token_budget_ollama", 15000))
        config.RAG_TOKEN_BUDGET_GEMINI = int(self.settings.get("rag_token_budget_gemini", 300000))
        config.ASSESSMENT_MIN_BLOCKS = int(self.settings.get("assessment_min_blocks", 5))
        config.INSTAGRAM_USERNAME = self.settings.get("instagram_username", "") or None
        config.DISPLAY_NAME = self.settings.get("display_name", "") or None

from src.utils.lazy_proxy import LazyProxy

settings_manager = LazyProxy(SettingsManager)
