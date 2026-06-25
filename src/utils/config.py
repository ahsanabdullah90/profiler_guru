import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Config:
    def __init__(self):
        self.GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        self.INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
        self.INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
        
        # Simple UI Auth
        self.APP_PASSWORD = os.getenv("APP_PASSWORD")
        
        # Cloud AI Master Toggle
        self.ENABLE_CLOUD_AI = os.getenv("ENABLE_CLOUD_AI", "true").lower() == "true"
        
        # Local LLM config
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini") # gemini or ollama
        self.OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
        self.OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        # Concurrency limit for thread synchronization
        self.SYNC_MAX_THREADS = int(os.getenv("SYNC_MAX_THREADS", 20))

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
        self.SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # 5 minutes
        self.DEVICE = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"

        # Cloud LLM Configuration
        self.CLOUD_API_KEY = os.getenv("CLOUD_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        self.CLOUD_PROVIDER = os.getenv("CLOUD_PROVIDER", "gemini")

        # Assessment & RAG Constants
        self.PERSONA_ASSESS_MAX_LOCAL_TOKENS = 64000
        self.TOKEN_ESTIMATION_FACTOR = 4  # chars per token
        self.DEEP_SCAN_DEFAULT = False

        # PDF Default Toggles
        self.PDF_INCLUDE_CHARTS = True
        self.PDF_INCLUDE_RAW_SNIPPETS = True
        self.PDF_INCLUDE_TEXTUAL_PROFILE = True

    def validate(self):
        # Synchronize GOOGLE_API_KEY and CLOUD_API_KEY
        if not self.CLOUD_API_KEY and self.GOOGLE_API_KEY:
            self.CLOUD_API_KEY = self.GOOGLE_API_KEY
        elif self.CLOUD_API_KEY and not self.GOOGLE_API_KEY:
            self.GOOGLE_API_KEY = self.CLOUD_API_KEY

        if self.ENABLE_CLOUD_AI and not self.CLOUD_API_KEY:
            print("Warning: CLOUD_API_KEY/GOOGLE_API_KEY not found in environment. Cloud AI will be unavailable.")
        
        if not self.APP_PASSWORD:
            print("Warning: APP_PASSWORD is not set in the environment. UI portal access will be disabled until configured.")

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
                    pass
            
            if new_chats_empty:
                import shutil
                try:
                    if self.DATA_DIR.exists():
                        shutil.rmtree(self.DATA_DIR, ignore_errors=True)
                    shutil.move(str(old_data_dir), str(self.DATA_DIR))
                    print(f"Migration: Successfully migrated historical data from {old_data_dir} to {self.DATA_DIR}")
                except Exception as e:
                    print(f"Migration Warning: Failed to move historical data: {e}")

        # Ensure application directories exist
        os.makedirs(self.DATA_DIR, exist_ok=True)
        os.makedirs(self.CHATS_DIR, exist_ok=True)
        os.makedirs(self.EXPORTS_DIR, exist_ok=True)

config = Config()

