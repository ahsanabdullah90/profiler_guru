import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    
    # Simple UI Auth
    APP_PASSWORD = os.getenv("APP_PASSWORD", "profile_guru")
    
    # Cloud AI Master Toggle
    ENABLE_CLOUD_AI = os.getenv("ENABLE_CLOUD_AI", "true").lower() == "true"
    
    # Local LLM config
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # gemini or ollama
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # Concurrency limit for thread synchronization
    SYNC_MAX_THREADS = int(os.getenv("SYNC_MAX_THREADS", 20))


    # Hardened Application Data Directory
    if os.name == "nt":
        DEFAULT_DATA_DIR = Path(os.getenv("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))) / "Profile_Guru"
    else:
        DEFAULT_DATA_DIR = Path(os.path.expanduser("~/.profile_guru"))
    
    DATA_DIR = Path(os.getenv("DATA_DIR", str(DEFAULT_DATA_DIR)))
    CHATS_DIR = DATA_DIR / "chats"
    EXPORTS_DIR = DATA_DIR / "exports"
    SETTINGS_PATH = EXPORTS_DIR / "settings.json"
    SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # 5 minutes
    DEVICE = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"

    # Cloud LLM Configuration
    CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
    CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "gemini")

    # Assessment & RAG Constants
    PERSONA_ASSESS_MAX_LOCAL_TOKENS = 64000
    TOKEN_ESTIMATION_FACTOR = 4  # chars per token
    DEEP_SCAN_DEFAULT = False

    # PDF Default Toggles
    PDF_INCLUDE_CHARTS = True
    PDF_INCLUDE_RAW_SNIPPETS = True
    PDF_INCLUDE_TEXTUAL_PROFILE = True

    @classmethod
    def validate(cls):
        # Synchronize GOOGLE_API_KEY and CLOUD_API_KEY
        if not cls.CLOUD_API_KEY and cls.GOOGLE_API_KEY:
            cls.CLOUD_API_KEY = cls.GOOGLE_API_KEY
        elif cls.CLOUD_API_KEY and not cls.GOOGLE_API_KEY:
            cls.GOOGLE_API_KEY = cls.CLOUD_API_KEY

        if cls.ENABLE_CLOUD_AI and not cls.CLOUD_API_KEY:
            print("Warning: CLOUD_API_KEY/GOOGLE_API_KEY not found in environment. Cloud AI will be unavailable.")
        
        # Ensure application directories exist
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.CHATS_DIR, exist_ok=True)
        os.makedirs(cls.EXPORTS_DIR, exist_ok=True)

config = Config()

