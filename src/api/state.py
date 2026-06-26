from src.engine.instagram_sync import InstagramSync, SyncManager
from src.storage.storage_manager import StorageManager
from src.utils.config import config

# Instantiate global shared engines for the FastAPI backend
sync_engine = InstagramSync()
sync_manager = SyncManager(sync_engine)
storage_manager = StorageManager(config.CHATS_DIR)
