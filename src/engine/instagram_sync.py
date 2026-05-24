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
        self.last_sync_time = {}

    def login(self, username, password, verification_code=None):
        try:
            if os.path.exists(self.session_path):
                self.cl.load_settings(self.session_path)
                try:
                    self.cl.get_timeline_feed()
                    logger.info("Instagram session loaded successfully.")
                    return "success", None
                except Exception:
                    logger.info("Session expired, attempting fresh login.")

            if verification_code:
                # This would be part of a two-step flow in reality
                pass

            self.cl.login(username, password)
            self.cl.dump_settings(self.session_path)
            logger.info(f"Logged in as {username}")
            return "success", None
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Login failed: {error_msg}")
            if "challenge_required" in error_msg:
                return "challenge", self.cl.last_json
            return "error", error_msg

    def fetch_new_messages(self):
        try:
            threads = self.cl.direct_threads(amount=20)
            for thread in threads:
                chat_name = thread.thread_title or "Unknown Chat"
                messages = self.cl.direct_messages(thread.id, amount=20)

                paths = self.sm.get_chat_paths(chat_name)

                # Sort messages by timestamp
                for msg in reversed(messages):
                    msg_id = msg.id
                    if msg_id in self.last_sync_time.get(thread.id, set()):
                        continue

                    text = msg.text or ""
                    timestamp = int(msg.timestamp.timestamp() * 1000)
                    sender = msg.user_id

                    media_type = None
                    media_local_path = None

                    # Handle Image
                    if msg.item_type == 'media' and msg.media:
                        if msg.media.media_type == 1: # Image
                            media_type = 'image'
                            try:
                                media_local_path = self.cl.photo_download(msg.media.pk, folder=paths['media_dir'])
                                description = media_processor.describe_image(media_local_path)
                                text += f"\n[Live Image Description: {description}]"
                            except Exception as e:
                                logger.error(f"Image download failed: {e}")

                    # Handle Voice Clip
                    elif msg.item_type == 'voice_media':
                        media_type = 'audio'
                        try:
                            media_local_path = self.cl.clip_download(msg.voice_media.media.pk, folder=paths['audio_dir'])
                            transcription = media_processor.transcribe_audio(media_local_path)
                            text += f"\n[Live Audio Transcription: {transcription}]"
                        except Exception as e:
                            logger.error(f"Audio download failed: {e}")

                    content, _, quarter_id = self.sm.save_message(chat_name, sender, text, timestamp, media_type, media_local_path)
                    rag_engine.add_messages_to_index(chat_name, quarter_id, content)

                    # Track synced messages
                    if thread.id not in self.last_sync_time:
                        self.last_sync_time[thread.id] = set()
                    self.last_sync_time[thread.id].add(msg_id)

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
        if hasattr(self, "_thread") and self._thread.is_alive():
            self._thread.join(timeout=5)
        self.is_running = False

    def _run(self):
        while not self._stop_event.is_set():
            logger.info("Running background sync...")
            self.fetch_new_messages()
            self._stop_event.wait(config.SYNC_INTERVAL)
