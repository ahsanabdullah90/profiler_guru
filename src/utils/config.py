import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        # Load Google API Key from keyring, falling back to .env
        self.GOOGLE_API_KEY = None
        try:
            import keyring
            self.GOOGLE_API_KEY = keyring.get_password("Profile_Guru", "google_api_key")
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Could not read GOOGLE_API_KEY from keyring")
        if not self.GOOGLE_API_KEY:
            self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

        # Multi-provider API keys (from env, keyring handled in settings_manager)
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENGODE_GO_API_KEY = os.getenv("OPENGODE_GO_API_KEY", "")
        self.OPENGODE_ZEN_API_KEY = os.getenv("OPENGODE_ZEN_API_KEY", "")

        # Load Instagram credentials from keyring, falling back to .env
        self.INSTAGRAM_USERNAME = None
        try:
            import keyring
            self.INSTAGRAM_USERNAME = keyring.get_password("Profile_Guru", "instagram_username")
        except Exception:
            import logging
            logging.getLogger(__name__).warning("Could not read INSTAGRAM_USERNAME from keyring")
        if not self.INSTAGRAM_USERNAME:
            self.INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")

        # Display name (loaded from settings; placeholder ensures attribute exists)
        self.DISPLAY_NAME = os.getenv("DISPLAY_NAME", "")

        # Simple UI Auth — must be bcrypt hashed
        raw_password = os.getenv("APP_PASSWORD")
        if raw_password:
            is_bcrypt = (
                raw_password.startswith(("$2a$", "$2b$", "$2y$"))
                and len(raw_password) == 60
            )
            if not is_bcrypt:
                raise ValueError(
                    "APP_PASSWORD must be a bcrypt hash. "
                    "Generate one with: python -c \"import bcrypt; print(bcrypt.hashpw(b'yourpassword', bcrypt.gensalt()).decode())\""
                )
        self.APP_PASSWORD = raw_password

        # JWT Authentication — must be explicitly set
        self.SECRET_KEY = os.getenv("SECRET_KEY")
        if not self.SECRET_KEY:
            raise ValueError(
                "SECRET_KEY environment variable is required. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        self.JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

        # CORS
        raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
        self.ALLOWED_ORIGINS: List[str] = [o.strip() for o in raw_origins.split(",") if o.strip()]

        # Cloud AI Master Toggle
        self.ENABLE_CLOUD_AI = os.getenv("ENABLE_CLOUD_AI", "true").lower() == "true"

        # Local LLM config
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama") # gemini or ollama
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
        # Per-provider model names — no hardcoded defaults; set via Settings → Models
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "")
        self.ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "")
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "")
        self.OPENGODE_GO_MODEL = os.getenv("OPENGODE_GO_MODEL", "")
        self.OPENGODE_ZEN_MODEL = os.getenv("OPENGODE_ZEN_MODEL", "")
        # OpenCode base URLs
        self.OPENGODE_GO_BASE_URL = os.getenv("OPENGODE_GO_BASE_URL", "https://opencode.ai/zen/go/v1")
        self.OPENGODE_ZEN_BASE_URL = os.getenv("OPENGODE_ZEN_BASE_URL", "https://opencode.ai/zen/v1")
        # Ollama timeout configuration (lazy-imported in OllamaClient to avoid circular import)
        self.OLLAMA_LIST_TIMEOUT = int(os.getenv("OLLAMA_LIST_TIMEOUT", 10))
        self.OLLAMA_GENERATE_TIMEOUT = int(os.getenv("OLLAMA_GENERATE_TIMEOUT", 120))
        self.OLLAMA_KEEP_ALIVE = int(os.getenv("OLLAMA_KEEP_ALIVE", "-1"))  # -1 = keep model loaded forever

        # Dynamic Embedding configuration (model selected in Settings → Models)
        self.EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama") # ollama or local
        self.EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")
        self.OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Hardened Application Data Directory
        if os.name == "nt":
            self.DEFAULT_DATA_DIR = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "Profile_Guru"
        else:
            self.DEFAULT_DATA_DIR = Path(os.path.expanduser("~/.profile_guru"))

        data_dir_env = os.getenv("DATA_DIR")
        if data_dir_env and data_dir_env.strip():
            self.DATA_DIR = Path(data_dir_env.strip())
        else:
            self.DATA_DIR = self.DEFAULT_DATA_DIR

        self.CHATS_DIR = self.DATA_DIR / "chats"
        self.EXPORTS_DIR = self.DATA_DIR / "exports"
        self.SETTINGS_PATH = self.EXPORTS_DIR / "settings.json"
        self.DEVICE = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"

        # Cloud LLM Configuration
        self.ACTIVE_PROVIDER = os.getenv("ACTIVE_PROVIDER", "ollama") # which provider is active
        self.CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "gemini")

        # Assessment & RAG Constants
        self.PERSONA_ASSESS_MAX_LOCAL_TOKENS = 64000
        self.TOKEN_ESTIMATION_FACTOR = 4  # chars per token
        self.DEEP_SCAN_DEFAULT = False
        self.RAG_RELEVANCY_THRESHOLD = float(os.getenv("RAG_RELEVANCY_THRESHOLD", 0.3))
        self.RAG_TOKEN_BUDGET_OLLAMA = int(os.getenv("RAG_TOKEN_BUDGET_OLLAMA", 15000))
        self.RAG_TOKEN_BUDGET_GEMINI = int(os.getenv("RAG_TOKEN_BUDGET_GEMINI", 300000))
        self.ASSESSMENT_MIN_BLOCKS = int(os.getenv("ASSESSMENT_MIN_BLOCKS", 5))

        # PDF Default Toggles
        self.PDF_INCLUDE_CHARTS = True
        self.PDF_INCLUDE_RAW_SNIPPETS = True
        self.PDF_INCLUDE_TEXTUAL_PROFILE = True

    def validate(self):
        # Synchronize legacy CLOUD_API_KEY with GOOGLE_API_KEY
        if not self.CLOUD_API_KEY and self.GOOGLE_API_KEY:
            self.CLOUD_API_KEY = self.GOOGLE_API_KEY
        elif self.CLOUD_API_KEY and not self.GOOGLE_API_KEY:
            self.GOOGLE_API_KEY = self.CLOUD_API_KEY
        # Also try loading other keys from env if not already set via keyring
        if not self.ANTHROPIC_API_KEY:
            self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
        if not self.OPENAI_API_KEY:
            self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

        # Self-healing migration from legacy "InstaSync" data directory
        if os.name == "nt":
            old_data_dir = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "InstaSync"
        else:
            old_data_dir = Path(os.path.expanduser("~/.instasync"))

        if old_data_dir.exists():
            new_chats_empty = True
            new_chats_dir = self.DATA_DIR / "chats"
            if new_chats_dir.exists():
                try:
                    if any(new_chats_dir.iterdir()):
                        new_chats_empty = False
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("Failed to scan legacy data directory for migration")

            if new_chats_empty:
                import shutil
                try:
                    if self.DATA_DIR.exists():
                        shutil.rmtree(self.DATA_DIR, ignore_errors=True)
                    shutil.move(str(old_data_dir), str(self.DATA_DIR))
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("Failed to migrate legacy data directory")

        # Ensure application directories exist
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.CHATS_DIR, exist_ok=True)
        os.makedirs(self.EXPORTS_DIR, exist_ok=True)

config = Config()

