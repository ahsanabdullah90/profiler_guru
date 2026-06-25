import os
import json
import time
import atexit
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from instagrapi import Client
from src.utils.config import config
from src.utils.logger import logger
from src.storage.storage_manager import StorageManager
from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine
from src.engine.metrics_engine import MetricsEngine
from src.utils.task_tracker import task_tracker

def is_supported_message(msg) -> bool:
    """Determine if a message should be processed in the live sync.
    Returns True for text or audio messages, False for reels or unsupported types.
    """
    # If it is a voice media message, it's supported
    if getattr(msg, "item_type", None) == "voice_media":
        return True
        
    # Check if this is a reel share or clip share
    item_type = getattr(msg, "item_type", None)
    if item_type in ["clip", "reel_share", "felix_share"]:
        return False

    # Check text for reel links
    text = getattr(msg, "text", "") or ""
    if "instagram.com/reel/" in text or "instagram.com/reels/" in text:
        return False
        
    # If the message has attachments, scan them
    attachments = getattr(msg, "attachments", [])
    if attachments:
        for att in attachments:
            att_type = att.get("type") if isinstance(att, dict) else getattr(att, "type", None)
            url = ""
            if isinstance(att, dict):
                url = att.get("payload", {}).get("url", "") or att.get("url", "")
            else:
                payload = getattr(att, "payload", {})
                url = payload.get("url", "") if isinstance(payload, dict) else getattr(payload, "url", "")
            
            if att_type == "audio" or (att_type == "video" and "voice" in url):
                return True
            if att_type in ["reel", "video", "image"] or "/reel/" in url:
                return False
                
    # If item_type is 'text' or we have text, it's supported
    if item_type == "text" or text.strip():
        return True
        
    return False

class InstagramSync:
    def __init__(self):
        self.cl = Client()
        
        # Save session file inside the hardened application data directory
        self.session_path = str(config.DATA_DIR / "session.json")
        self.last_sync_path = config.DATA_DIR / "last_sync.json"
        
        self.sm = StorageManager(config.CHATS_DIR)
        self.metrics_engine = MetricsEngine()
        
        # Thread safety lock for concurrent file writes and ChromaDB updates
        self.write_lock = threading.Lock()
        
        # Persistent deduplication maps:
        # last_sync_time: thread_id -> last synced timestamp (ms)
        self.last_sync_time = {}
        # last_sync_run: chat_name -> epoch timestamp (float) of last successful sync/import run
        self.last_sync_run = {}
        # synced_message_ids: thread_id -> set of message IDs
        self.synced_message_ids = {}
        
        # Thread-safe tracking of active background syncing contacts
        self.active_syncs = set()
        
        # Track active sync progress
        self.sync_progress_lock = threading.Lock()
        self.sync_progress_current = 0
        
        self._load_sync_state()
        
        # Trigger background backfill on startup if not done yet
        if not self.metrics_engine.is_backfill_done():
            threading.Thread(target=self._run_background_backfill, daemon=True).start()

    def _run_background_backfill(self):
        """Runs the historical metrics backfill in a separate background thread."""
        task_id = "backfill_historical"
        logger.info("Starting background backfill of historical chat metrics...")
        task_tracker.register_task(task_id, "Historical Database Backfill")
        
        def progress_cb(current, total):
            task_tracker.update_task(task_id, current, total)
            
        try:
            self.metrics_engine.backfill_existing_logs(progress_callback=progress_cb)
            task_tracker.complete_task(task_id)
            logger.info("Background historical backfill completed successfully.")
        except Exception as e:
            logger.error(f"Failed to backfill historical logs: {e}")
            task_tracker.fail_task(task_id, str(e))

    def _load_sync_state(self):
        """Loads persistent deduplication state from disk."""
        if self.last_sync_path.exists():
            try:
                with open(self.last_sync_path, "r", encoding='utf-8') as f:
                    data = json.load(f)
                    self.last_sync_time = data.get("last_sync_time", {})
                    self.last_sync_run = data.get("last_sync_run", {})
                    # Backward-compatible loading of synced message IDs (supporting both list and dict formats)
                    raw_ids = data.get("synced_message_ids", {})
                    self.synced_message_ids = {}
                    for k, v in raw_ids.items():
                        if isinstance(v, dict):
                            self.synced_message_ids[k] = {mid: int(ts) for mid, ts in v.items()}
                        elif isinstance(v, list):
                            last_ts = self.last_sync_time.get(k, 0)
                            self.synced_message_ids[k] = {mid: last_ts for mid in v}
                logger.info("Persistent sync state loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load last_sync.json: {e}")

    def _save_sync_state(self):
        """Saves persistent deduplication state to disk. Protected by write_lock."""
        try:
            # Bounded set: prune message IDs older than 30 days relative to the thread's last sync time
            thirty_days_ms = 30 * 24 * 3600 * 1000
            pruned_ids = {}
            for thread_id, ids_dict in self.synced_message_ids.items():
                cutoff = self.last_sync_time.get(thread_id, 0) - thirty_days_ms
                pruned_ids[thread_id] = {
                    mid: ts for mid, ts in ids_dict.items() if ts >= cutoff
                }
            self.synced_message_ids = pruned_ids

            data = {
                "last_sync_time": self.last_sync_time,
                "last_sync_run": self.last_sync_run,
                "synced_message_ids": self.synced_message_ids
            }
            with open(self.last_sync_path, "w", encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug("Persistent sync state saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save last_sync.json: {e}")

    def login(self, username, password, verification_code=None):
        try:
            # 1. Try to reuse an existing saved session (only if not in 2FA flow)
            if not verification_code and os.path.exists(self.session_path):
                self.cl.load_settings(self.session_path)
                try:
                    self.cl.get_timeline_feed()
                    logger.info("Instagram session loaded successfully.")
                    return "success", None
                except Exception:
                    logger.info("Session expired or invalid. Clearing stale session and starting fresh.")
                    # Reset the Client to a clean state to avoid corrupted internal state
                    self.cl = Client()
                    try:
                        os.remove(self.session_path)
                    except OSError:
                        pass

            # 2. If a 2FA code was provided, try the two-step flow first
            if verification_code:
                logger.info("Attempting two_factor_login with provided code...")
                try:
                    self.cl.two_factor_login(verification_code)
                    self.cl.dump_settings(self.session_path)
                    logger.info(f"Logged in via 2FA as {username}")
                    return "success", None
                except Exception as two_fa_err:
                    logger.warning(f"two_factor_login failed ({two_fa_err}), trying direct login with verification_code...")
                    # Fallback: reinit client and try passing code directly to login()
                    self.cl = Client()
                    try:
                        self.cl.login(username, password, verification_code=verification_code)
                        self.cl.dump_settings(self.session_path)
                        logger.info(f"Logged in via direct 2FA as {username}")
                        return "success", None
                    except Exception as direct_err:
                        error_msg = str(direct_err)
                        logger.error(f"Direct 2FA login also failed: {error_msg}")
                        return "error", error_msg

            # 3. Standard login (no code provided yet)
            if not username or not password:
                return "error", "Credentials not provided and no valid session found."
                
            logger.info("Attempting standard login...")
            self.cl.login(username, password)
            self.cl.dump_settings(self.session_path)
            logger.info(f"Logged in as {username}")
            return "success", None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Login failed: {error_msg}")
            if "two-factor" in error_msg.lower() or "verification_code" in error_msg.lower() or "2fa" in error_msg.lower():
                return "2fa_required", error_msg
            if "challenge_required" in error_msg:
                return "challenge", self.cl.last_json
            return "error", error_msg

    def sync_thread_messages(self, thread):
        """Syncs a single direct thread.
        Paginates backwards until the last synced timestamp is reached.
        Runs concurrently inside a ThreadPoolExecutor.
        """
        chat_name = thread.thread_title or "Unknown Chat"
        thread_id = str(thread.id)
        
        # Track active sync thread-safely
        with self.write_lock:
            self.active_syncs.add(chat_name)
        
        try:
            # Build a mapping of user IDs to display names/usernames in this thread
            user_map = {}
            for u in thread.users:
                user_map[str(u.pk)] = u.full_name or u.username
            
            # Map the current logged-in user
            try:
                if self.cl.user_id:
                    user_map[str(self.cl.user_id)] = self.cl.username or "Me"
            except Exception:
                pass

            # Load sync boundary (last synced timestamp in ms)
            last_ts = self.last_sync_time.get(thread_id, 0)
            
            # Fetch up to 100 messages per thread per cycle to prevent rate limits.
            messages = self.cl.direct_messages(thread.id, amount=100)

            if not messages:
                return

            paths = self.sm.get_chat_paths(chat_name)
            rag_batch = []
            
            # Thread-safe initialization of synced IDs map
            with self.write_lock:
                if thread_id not in self.synced_message_ids:
                    self.synced_message_ids[thread_id] = {}

            # Process messages chronologically (oldest first)
            for msg in reversed(messages):
                # Filter out unsupported messages (reels, video/images, etc.)
                if not is_supported_message(msg):
                    logger.debug(f"Skipping unsupported Reel or media message {msg.id} in thread '{chat_name}'")
                    continue

                msg_id = str(msg.id)
                timestamp = int(msg.timestamp.timestamp() * 1000)
                
                # Retrieve human-readable sender name from mapping
                sender_id = str(msg.user_id)
                sender = user_map.get(sender_id, sender_id)
                
                # Deduplicate using both message ID and boundary timestamp
                if msg_id in self.synced_message_ids[thread_id]:
                    continue
                if timestamp < last_ts:
                    continue

                text = msg.text or ""
                media_type = None
                media_local_path = None

                # Handle Voice Clip (No image handling per spec)
                if msg.item_type == 'voice_media':
                    media_type = 'audio'
                    try:
                        if msg.media and getattr(msg.media, 'audio_url', None):
                            from urllib.parse import urlparse
                            url = str(msg.media.audio_url)
                            fname = urlparse(url).path.rsplit("/", 1)[1]
                            ext = fname.rsplit(".", 1)[1] if "." in fname else "m4a"
                            ext = ext.split("?")[0]
                            filename = f"{msg_id}.{ext}"
                            media_local_path = os.path.join(paths['audio_dir'], filename)
                            
                            response = requests.get(url, stream=True, timeout=15)
                            response.raise_for_status()
                            with open(media_local_path, "wb") as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    f.write(chunk)
                                    
                            transcription = media_processor.transcribe_audio(media_local_path)
                            text += f"\n[Live Audio Transcription: {transcription}]"
                        else:
                            logger.error(f"Voice message {msg_id} has no media or audio URL.")
                    except Exception as e:
                        logger.error(f"Audio download failed for message {msg_id}: {e}")

                # Thread-safe storage writing and in-memory tracking updates
                with self.write_lock:
                    content, _, month_id = self.sm.save_message(
                        chat_name, sender, text, timestamp, media_type, media_local_path
                    )
                    
                    # Record metric in MetricsEngine
                    self.metrics_engine.increment_message(chat_name, timestamp)
                    
                    rag_batch.append((chat_name, month_id, content))
                    self.synced_message_ids[thread_id][msg_id] = timestamp
                    self.last_sync_time[thread_id] = max(self.last_sync_time.get(thread_id, 0), timestamp)

            # Thread-safe batch index update and persistent save
            with self.write_lock:
                if rag_batch:
                    rag_engine.add_messages_batch(rag_batch)
                self.last_sync_run[chat_name] = time.time()
                self._save_sync_state()
                    
        except Exception as e:
            logger.error(f"Failed to sync thread '{chat_name}' ({thread_id}): {e}")
        finally:
            # Ensure we always remove the contact from active syncs
            with self.write_lock:
                self.active_syncs.discard(chat_name)
                
            # Update sync task progress in global tracker
            with self.sync_progress_lock:
                self.sync_progress_current += 1
                task_tracker.update_task("instagram_sync", self.sync_progress_current)

    def record_sync_run(self, chat_name: str):
        """Records the completion of a sync or import run for a contact."""
        with self.write_lock:
            self.last_sync_run[chat_name] = time.time()
            self._save_sync_state()

    def fetch_new_messages(self):
        """Fetches the latest 50 direct threads and syncs them concurrently."""
        task_id = "instagram_sync"
        try:
            logger.info("Fetching direct message threads...")
            threads = self.cl.direct_threads(amount=50)
            
            if not threads:
                logger.info("No active threads found.")
                return

            total_threads = len(threads)
            task_tracker.register_task(task_id, "Instagram Account Sync", total=total_threads)
            
            with self.sync_progress_lock:
                self.sync_progress_current = 0

            # Process threads in parallel using ThreadPoolExecutor
            logger.info(f"Syncing {total_threads} threads concurrently with up to {config.SYNC_MAX_THREADS} workers...")
            with ThreadPoolExecutor(max_workers=config.SYNC_MAX_THREADS) as executor:
                # Map sync_thread_messages to threads.
                # If cancellation is requested in the middle, executor will still finish scheduled items,
                # but we can check cancellation in individual threads.
                executor.map(self.sync_thread_messages, threads)
                
            task_tracker.complete_task(task_id)
            logger.info("Sync cycle completed successfully.")
        except Exception as e:
            logger.error(f"Error during sync execution: {e}")
            task_tracker.fail_task(task_id, str(e))


class SyncManager:
    """Manages the lifecycle, execution, and graceful shutdown of the background sync thread."""
    def __init__(self, sync_engine: InstagramSync):
        self.sync_engine = sync_engine
        self.is_running = False
        self._stop_event = threading.Event()
        self._thread = None
        
        # Register graceful shutdown hooks
        atexit.register(self.stop)

    def start(self):
        if self.is_running:
            logger.info("Sync thread is already running.")
            return
        self.is_running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("Background sync manager started.")

    def stop(self):
        if not self.is_running:
            return
        logger.info("Shutting down background sync thread gracefully...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self.is_running = False
        logger.info("Sync thread joined and terminated successfully.")

    def _run(self):
        while not self._stop_event.is_set():
            logger.info("Running background sync cycle...")
            # Register sync task in task tracker
            self.sync_engine.fetch_new_messages()
            # Wait for interval or stop flag
            self._stop_event.wait(config.SYNC_INTERVAL)
