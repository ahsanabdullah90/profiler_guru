import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME")
    INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD")
    CHATS_DIR = os.getenv("CHATS_DIR", "chats")
    SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", 300))  # 5 minutes
    DEVICE = "cuda" if os.getenv("USE_GPU", "false").lower() == "true" else "cpu"

    @classmethod
    def validate(cls):
        if not cls.GOOGLE_API_KEY:
            print("Warning: GOOGLE_API_KEY not found in environment.")
        if not os.path.exists(cls.CHATS_DIR):
            os.makedirs(cls.CHATS_DIR)

config = Config()
