import atexit
import json
import os
import random
import threading
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from instagrapi import Client

from src.engine.media_processor import media_processor
from src.engine.metrics_engine import MetricsEngine
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.logger import logger
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


def call_ig_with_backoff(func, *args, **kwargs):
    """Wraps an instagrapi/Instagram API call with exponential backoff on rate limits or network issues."""
    import time
    max_retries = 5
    base_delay = 2.0  # start with 2 seconds
    factor = 2.0
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            err_str = str(e).lower()
            is_transient = (
                "429" in err_str or 
                "rate limit" in err_str or 
                "feedback_required" in err_str or 
                "please wait" in err_str or 
                "wait" in err_str or 
                "connection" in err_str or 
                "timeout" in err_str
            )
            if is_transient and attempt < max_retries - 1:
                delay = base_delay * (factor ** attempt)
                logger.warning(f"Instagram API call failed: {e}. Retrying in {delay:.2f} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(delay)
            else:
                raise e


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

        # Trigger background vacuum on startup with a 60-second delay to avoid blocking boot
        threading.Thread(target=self._run_background_vacuum, daemon=True).start()

    def _run_background_vacuum(self):
        """Runs the vector store vacuum in a separate background thread after a startup delay."""
        time.sleep(60.0)
        task_id = "vacuum_orphans"
        logger.info("Starting background vacuum of orphaned vectors...")
        task_tracker.register_task(task_id, "Vector DB Garbage Collection")
        try:
            from src.engine.rag_engine import rag_engine
            deleted = rag_engine.vacuum_orphaned_vectors()
            task_tracker.complete_task(task_id)
            logger.info(f"Background vacuum completed. Deleted {deleted} orphaned vectors.")
        except Exception as e:
            task_tracker.fail_task(task_id, str(e))
            logger.error(f"Failed to run background vacuum: {e}")

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
                with open(self.last_sync_path, encoding='utf-8') as f:
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

    def _save_to_keyring(self, username, password):
        """Helper to save Instagram credentials to OS keyring."""
        if username and password:
            try:
                import keyring
                keyring.set_password("Profile_Guru", "instagram_username", username)
                keyring.set_password("Profile_Guru", "instagram_password", password)
                logger.info("Saved Instagram credentials to OS keyring.")
            except Exception as e:
                logger.error(f"Failed to save credentials to OS keyring: {e}")

    def login(self, username, password, verification_code=None):
        # Fall back to keyring/env credentials if not explicitly passed
        active_username = username or config.INSTAGRAM_USERNAME
        active_password = password or config.INSTAGRAM_PASSWORD

        try:
            # 1. If a 2FA code was provided, try the 2FA flow first (skip session file check)
            if verification_code:
                logger.info("Attempting two_factor_login with provided code...")
                try:
                    self.cl.two_factor_login(verification_code)
                    self.cl.dump_settings(self.session_path)
                    logger.info(f"Logged in via 2FA as {active_username}")
                    self._save_to_keyring(active_username, active_password)
                    return "success", None
                except Exception as two_fa_err:
                    logger.warning(f"two_factor_login failed ({two_fa_err}), trying direct login with verification_code...")
                    # Fallback: reinit client and try passing code directly to login()
                    self.cl = Client()
                    try:
                        self.cl.login(active_username, active_password, verification_code=verification_code)
                        self.cl.dump_settings(self.session_path)
                        logger.info(f"Logged in via direct 2FA as {active_username}")
                        self._save_to_keyring(active_username, active_password)
                        return "success", None
                    except Exception as direct_err:
                        error_msg = str(direct_err)
                        logger.error(f"Direct 2FA login also failed: {error_msg}")
                        return "error", error_msg

            # 2. Try to reuse an existing saved session (only if not in 2FA flow)
            elif os.path.exists(self.session_path):
                try:
                    self.cl.load_settings(self.session_path)
                    # Verify session validity by fetching feed
                    self.cl.get_timeline_feed()
                    logger.info("Instagram session restored and validated successfully.")
                    return "success", None
                except Exception as restore_err:
                    logger.info(f"Session restoration failed or expired: {restore_err}. Attempting fresh login fallback...")
                    
                    # If we have credentials (passed or from keyring/env), try to log in fresh
                    if active_username and active_password:
                        try:
                            # Use existing Client settings to preserve device fingerprint
                            self.cl.login(active_username, active_password)
                            
                            # Clean the stale session file now that fresh login succeeded (keeps tests green)
                            try:
                                os.remove(self.session_path)
                            except OSError:
                                pass
                                
                            self.cl.dump_settings(self.session_path)
                            logger.info(f"Logged in fresh to restore session as {active_username}")
                            self._save_to_keyring(active_username, active_password)
                            return "success", None
                        except Exception as fresh_err:
                            logger.error(f"Fresh login fallback failed: {fresh_err}")
                            return "error", f"Session expired and fresh login failed: {fresh_err}"
                    else:
                        # No credentials available (e.g., offline startup restore and no keyring/env settings)
                        logger.warning("Session expired and no credentials available for fresh login.")
                        return "error", f"Session expired/invalid: {restore_err}"

            # 3. Standard login (no code provided yet)
            if not active_username or not active_password:
                return "error", "Credentials not provided and no valid session found."

            logger.info("Attempting standard login...")
            self.cl.login(active_username, active_password)
            self.cl.dump_settings(self.session_path)
            logger.info(f"Logged in as {active_username}")
            self._save_to_keyring(active_username, active_password)
            return "success", None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Login failed: {error_msg}")
            if "two-factor" in error_msg.lower() or "verification_code" in error_msg.lower() or "2fa" in error_msg.lower():
                return "2fa_required", error_msg
            if "challenge_required" in error_msg:
                challenge_url = None
                if isinstance(self.cl.last_json, dict):
                    challenge_url = (
                        self.cl.last_json.get("challenge", {}).get("url")
                        or self.cl.last_json.get("challenge", {}).get("api_path")
                    )
                    if challenge_url and not challenge_url.startswith("http"):
                        challenge_url = f"https://www.instagram.com{challenge_url}"
                return "challenge", challenge_url
            return "error", error_msg

    def sync_thread_messages(self, thread, stop_event=None):
        """Syncs a single direct thread.
        Paginates backwards until the last synced timestamp is reached.
        Runs sequentially with human-paced message processing.
        """
        _stop = stop_event or threading.Event()
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

            # Fetch up to 20 messages per thread per cycle to simulate human scroll.
            messages = call_ig_with_backoff(self.cl.direct_messages, thread.id, amount=20)

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
                            fname = Path(urlparse(url).path).name
                            ext = Path(fname).suffix.lstrip(".") if "." in fname else "m4a"
                            ext = ext.split("?")[0]
                            filename = f"{msg_id}.{ext}"
                            media_local_path = str(Path(paths['audio_dir']) / filename)

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

                    # Simulate human reading time between messages (0.5–1.5 s)
                    if not _stop.is_set():
                        _stop.wait(timeout=random.uniform(0.5, 1.5))

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

    def _get_humanized_interval(self) -> float:
        """Returns a Gaussian-jittered sync interval based on hour of day.
        Daytime (08–23): μ=5 min, σ=1 min, clamped to [2, 30] min.
        Nighttime (23–08): μ=15 min, σ=5 min, clamped to [2, 30] min.
        """
        hour = datetime.now().hour
        if 8 <= hour < 23:
            interval = random.gauss(mu=300, sigma=60)
        else:
            interval = random.gauss(mu=900, sigma=300)
        return max(120.0, min(1800.0, interval))   # clamp: [2 min, 30 min]

    def fetch_new_messages(self, stop_event=None):
        """Fetches the latest direct threads and syncs them sequentially.
        Uses randomized inter-thread delays to mimic human app behavior.
        """
        _stop = stop_event or threading.Event()
        task_id = "instagram_sync"
        try:
            logger.info("Fetching direct message threads...")
            threads = call_ig_with_backoff(self.cl.direct_threads, amount=20)  # reduced from 50

            if not threads:
                logger.info("No active threads found.")
                return

            total_threads = len(threads)
            task_tracker.register_task(task_id, "Instagram Account Sync (Human-Paced)", total=total_threads)

            with self.sync_progress_lock:
                self.sync_progress_current = 0

            logger.info(f"Human-paced sequential sync of {total_threads} threads...")

            for thread in threads:
                if _stop.is_set():
                    logger.info("Stop signal received — aborting sync mid-cycle.")
                    break
                # Simulate human delay between opening each chat (2–5 s)
                _stop.wait(timeout=random.uniform(2.0, 5.0))
                if _stop.is_set():
                    break
                self.sync_thread_messages(thread, stop_event=_stop)

            task_tracker.complete_task(task_id)
            logger.info("Human-paced sync cycle completed.")
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
        """Background sync loop with human-paced timing and graceful exception handling."""
        consecutive_errors = 0

        while not self._stop_event.is_set():
            hour = time.localtime().tm_hour
            is_nighttime = not (8 <= hour < 23)

            # Nighttime: 10 % chance to skip cycle entirely (simulating sleep)
            if is_nighttime and random.random() < 0.10:
                logger.info("Nighttime: randomly skipping sync cycle (simulating sleep).")
                interval = self.sync_engine._get_humanized_interval()
                self._stop_event.wait(interval)
                continue

            # Skip cycle if user is actively using the UI (within the last 60 s)
            idle_secs = time.time() - config.last_user_activity
            if idle_secs < 60:
                logger.debug(f"User active {idle_secs:.0f}s ago — skipping sync to avoid API contention.")
                self._stop_event.wait(30)
                continue

            logger.info("Running background sync cycle...")
            try:
                self.sync_engine.fetch_new_messages(stop_event=self._stop_event)
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Sync cycle failed (attempt {consecutive_errors}): {e}")

                if consecutive_errors >= 3:
                    cooldown = 1800  # 30 minutes
                    logger.warning(f"3 consecutive errors — entering 30-minute cooldown.")
                    consecutive_errors = 0
                else:
                    cooldown = random.uniform(300, 600)   # 5–10 minutes
                    logger.warning(f"Sync error — pausing {cooldown:.0f}s before retry.")

                self._stop_event.wait(cooldown)
                continue

            interval = self.sync_engine._get_humanized_interval()
            logger.info(f"Next sync in {interval / 60:.1f} min.")
            self._stop_event.wait(interval)
