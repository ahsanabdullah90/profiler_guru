import os
import queue
import re
import threading
import time

from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.logger import logger

_PLACEHOLDER_RE = re.compile(r"\[Audio Transcription: Processing...\]")
_AUDIO_MARKER_RE = re.compile(r"\[Audio\]\(\.\./Audio/(.+)\)")
_HEADER_RE = re.compile(r"^### \[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] (.+)$")


class TranscriptionQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Transcription queue background worker thread started.")
        self._recover_orphans()

    def _recover_orphans(self):
        """Scan existing markdown files for orphaned [Audio Transcription: Processing...]
        placeholders and re-enqueue them. Runs once at startup."""
        chats_root = config.CHATS_DIR
        if not os.path.exists(chats_root):
            return
        recovered = 0
        for contact in os.listdir(chats_root):
            chats_dir = os.path.join(chats_root, contact, "Chats")
            if not os.path.isdir(chats_dir):
                continue
            for fname in os.listdir(chats_dir):
                if not fname.endswith(".md"):
                    continue
                month_id = fname[:-3]
                fpath = os.path.join(chats_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue
                for block in content.split("---"):
                    block_strip = block.strip()
                    if not _PLACEHOLDER_RE.search(block_strip):
                        continue
                    lines = block_strip.split("\n")
                    header_match = _HEADER_RE.match(lines[0].strip()) if lines else None
                    if not header_match:
                        continue
                    time_str, sender = header_match.groups()
                    audio_match = _AUDIO_MARKER_RE.search(block_strip)
                    if not audio_match:
                        continue
                    audio_filename = audio_match.group(1)
                    audio_path = os.path.join(chats_root, contact, "Audio", audio_filename)
                    if not os.path.exists(audio_path):
                        logger.warning(f"Orphan placeholder found but audio file missing: {audio_path}")
                        continue
                    logger.info(f"Recovered orphan transcription task for {contact} - {sender} [{time_str}]")
                    self.enqueue(contact, month_id, sender, time_str, audio_path)
                    recovered += 1
        if recovered:
            logger.info(f"Recovered {recovered} orphaned transcription tasks.")

    def enqueue(self, chat_name: str, month_id: str, sender: str, time_str: str, audio_path: str):
        """Pushes a transcription task to the queue."""
        logger.info(f"Enqueuing transcription task for {chat_name} - {sender} [{time_str}]")
        self.queue.put((chat_name, month_id, sender, time_str, audio_path))

    def _worker_loop(self):
        while True:
            try:
                task = self.queue.get()
                if task is None:
                    break

                chat_name, month_id, sender, time_str, audio_path = task
                logger.info(f"Processing transcription task for {chat_name} - {sender} [{time_str}]")

                try:
                    transcription = media_processor.transcribe_audio(audio_path)
                except Exception as e:
                    logger.error(f"Failed to transcribe {audio_path}: {e}")
                    transcription = "Transcription failed."

                # Atomic in-place update
                sm = StorageManager(config.CHATS_DIR)
                paths = sm.get_chat_paths(chat_name)
                file_path = os.path.join(paths["chats_dir"], f"{month_id}.md")
                if os.path.exists(file_path):
                    with StorageManager.get_lock(file_path):
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                content = f.read()

                            blocks = content.split("---")
                            target_header = f"### [{time_str}] {sender}"

                            old_block = None
                            new_block = None

                            for i, block in enumerate(blocks):
                                block_strip = block.strip()
                                if block_strip.startswith(target_header):
                                    placeholder = "[Audio Transcription: Processing...]"
                                    if placeholder in block_strip:
                                        old_block = block
                                        replacement = f"[Imported Audio Transcription: {transcription}]"
                                        blocks[i] = block.replace(placeholder, replacement)
                                        new_block = blocks[i]
                                        break

                            if old_block and new_block:
                                # Atomic write: tmp file then replace
                                new_content = "---".join(blocks)
                                tmp_path = file_path + ".tmp"
                                with open(tmp_path, "w", encoding="utf-8") as f:
                                    f.write(new_content)
                                os.replace(tmp_path, file_path)
                                logger.info(f"Successfully updated markdown file in-place for {chat_name} - {sender} [{time_str}]")

                                try:
                                    rag_engine.update_transcribed_message(chat_name, month_id, old_block, new_block)
                                    logger.info(f"Successfully re-indexed transcribed chunk in ChromaDB for {chat_name}")
                                except Exception as e:
                                    logger.error(f"Failed to update RAG vector store for {chat_name}: {e}")

                                # Invalidate contacts cache so the snippet updates
                                try:
                                    from src.utils.redis_client import invalidate_contacts_cache
                                    invalidate_contacts_cache()
                                except Exception:
                                    pass
                            else:
                                logger.warning(f"Could not find target message block or placeholder in {file_path} for {sender} [{time_str}]")

                        except Exception as e:
                            logger.error(f"Failed to write transcription to file {file_path}: {e}")
                else:
                    logger.error(f"Markdown file {file_path} does not exist for in-place update.")

                self.queue.task_done()
            except Exception as e:
                logger.error(f"Error in transcription worker loop: {e}")
                time.sleep(1.0)


transcription_queue = TranscriptionQueue()
