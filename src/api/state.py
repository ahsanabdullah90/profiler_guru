from src.engine.instagram_sync import InstagramSync, SyncManager

# Instantiate global shared engines for the FastAPI backend
sync_engine = InstagramSync()
sync_manager = SyncManager(sync_engine)
