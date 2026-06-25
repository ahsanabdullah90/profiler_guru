import json
import os
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger

DEFAULT_SETTINGS = {
    "cloud_api_key": "",
    "cloud_provider": "gemini",
    "deep_scan_default": False,
    "pdf_include_charts": True,
    "pdf_include_raw_snippets": True,
    "pdf_include_textual_profile": True,
    "report_sections_order": ["textual_profile", "charts", "snippets"]
}

class SettingsManager:
    def __init__(self):
        self.settings_path = Path(config.SETTINGS_PATH)
        self.settings = {}
        self.load()

    def load(self):
        """Loads settings from disk or initializes defaults."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
                logger.info(f"Loaded settings from {self.settings_path}")
            except Exception as e:
                logger.error(f"Failed to load settings from {self.settings_path}: {e}")
                self.settings = dict(DEFAULT_SETTINGS)
        else:
            self.settings = dict(DEFAULT_SETTINGS)
            # Default cloud API key from config (if set in .env initially)
            if config.CLOUD_API_KEY:
                self.settings["cloud_api_key"] = config.CLOUD_API_KEY
            self.save()
            
        self._apply_to_config()

    def save(self):
        """Saves current settings to disk."""
        try:
            os.makedirs(self.settings_path.parent, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
            logger.info(f"Saved settings to {self.settings_path}")
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
        # Also preserve .env defaults if available
        if os.getenv("CLOUD_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            self.settings["cloud_api_key"] = os.getenv("CLOUD_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.save()
        self._apply_to_config()

    def _apply_to_config(self):
        """Applies relevant settings back to the global Config object so they take effect immediately."""
        config.CLOUD_API_KEY = self.settings.get("cloud_api_key", config.CLOUD_API_KEY)
        config.CLOUD_PROVIDER = self.settings.get("cloud_provider", config.CLOUD_PROVIDER)
        config.DEEP_SCAN_DEFAULT = self.settings.get("deep_scan_default", config.DEEP_SCAN_DEFAULT)
        config.PDF_INCLUDE_CHARTS = self.settings.get("pdf_include_charts", config.PDF_INCLUDE_CHARTS)
        config.PDF_INCLUDE_RAW_SNIPPETS = self.settings.get("pdf_include_raw_snippets", config.PDF_INCLUDE_RAW_SNIPPETS)
        config.PDF_INCLUDE_TEXTUAL_PROFILE = self.settings.get("pdf_include_textual_profile", config.PDF_INCLUDE_TEXTUAL_PROFILE)

from src.utils.lazy_proxy import LazyProxy

settings_manager = LazyProxy(SettingsManager)
