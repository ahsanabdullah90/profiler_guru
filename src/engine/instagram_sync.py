import os
import time
import threading
from instagrapi import Client
from src.utils.config import config
from src.utils.logger import logger
from src.storage.storage_manager import StorageManager
from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine

class InstagramSync:
    def __init__(self):
        self.cl = Client()
        self.session_path = "session.json"
        self.sm = StorageManager(config.CHATS_DIR)
        self.is_running = False
        self._stop_event = threading.Event()

    def login(self, username, password):
        try:
            if os.path.exists(self.session_path):
                self.cl.load_settings(self.session_path)
                try:
                    self.cl.get_timeline_feed()
                    logger.info("Instagram session loaded successfully.")
                    return True
                except Exception:
                    logger.info("Session expired, attempting fresh login.")

            self.cl.login(username, password)
            self.cl.dump_settings(self.session_path)
            logger.info(f"Logged in as {username}")
            return True
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False

    def fetch_new_messages(self):
        try:
            threads = self.cl.direct_threads(amount=20)
            for thread in threads:
                chat_name = thread.thread_title or "Unknown Chat"
                messages = self.cl.direct_messages(thread.id, amount=20)

                paths = self.sm.get_chat_paths(chat_name)

                for msg in reversed(messages):
                    # Simple duplicate check could be added here based on message ID
                    text = msg.text or ""
                    timestamp = int(msg.timestamp.timestamp() * 1000)
                    sender = msg.user_id # Could resolve to username

                    media_type = None
                    media_local_path = None

                    # Handle media for live sync
                    if msg.clip: # Example for video/audio clip
                        # Download logic would go here
                        pass

                    content, _, quarter_id = self.sm.save_message(chat_name, sender, text, timestamp, media_type, media_local_path)
                    rag_engine.add_messages_to_index(chat_name, quarter_id, content)

            logger.info("Sync completed.")
        except Exception as e:
            logger.error(f"Error during sync: {e}")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self.is_running = False

    def _run(self):
        while not self._stop_event.is_set():
            logger.info("Running background sync...")
            self.fetch_new_messages()
            self._stop_event.wait(config.SYNC_INTERVAL)
