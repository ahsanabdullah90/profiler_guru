import hashlib
import os
import threading
from datetime import datetime

from src.utils.logger import logger
from src.utils.sanitize import sanitize_contact_name


class StorageManager:
    """Manages the local file system organization of Instagram chat logs and audio clips.

    Data is structured on disk per contact under:
    chats/<contact_name>/
    ├── Chats/   ← Quarterly markdown logs (YYYY_QN.md)
    └── Audio/   ← Synced voice messages
    """
    _locks: dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    @classmethod
    def get_lock(cls, key: str) -> threading.Lock:
        """Retrieves or creates a thread lock for a specific key (e.g. file path)."""
        with cls._locks_lock:
            if key not in cls._locks:
                cls._locks[key] = threading.Lock()
            return cls._locks[key]

    def __init__(self, base_dir="chats"):
        """Initializes the StorageManager with a root chat directory.

        Args:
            base_dir (str): Root folder path where all contact logs will be saved.
        """
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_month_filename(self, dt: datetime) -> str:
        """Determines the appropriate monthly file name for a given datetime object.

        Args:
            dt (datetime): The datetime representation of the message timestamp.

        Returns:
            str: Filename formatted as 'YYYY_MM.md' (e.g., '2026_06.md').
        """
        return f"{dt.year}_{dt.month:02d}.md"

    def get_chat_paths(self, chat_name: str) -> dict:
        """Sanitizes the contact name and retrieves/creates directory paths.

        Args:
            chat_name (str): The raw username or thread title of the contact.

        Returns:
            dict: Directory paths for 'chat_root', 'chats_dir', and 'audio_dir'.
        """
        sanitized_name = sanitize_contact_name(chat_name)

        chat_root = os.path.join(self.base_dir, sanitized_name)
        chats_dir = os.path.join(chat_root, "Chats")
        audio_dir = os.path.join(chat_root, "Audio")

        os.makedirs(chats_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        return {
            "chat_root": chat_root,
            "chats_dir": chats_dir,
            "audio_dir": audio_dir
        }

    def save_message(self, chat_name: str, sender: str, text: str, timestamp, media_type: str | None = None, media_local_path: str | None = None) -> tuple:
        """Formats and appends a single message to the appropriate quarterly markdown file.

        Supports bilingual text contents (Urdu & English script).

        Args:
            chat_name (str): The raw contact username/thread title.
            sender (str): The sender's username or user ID.
            text (str): The textual body of the message.
            timestamp: Epoch timestamp in milliseconds, or a datetime object.
            media_type (str, optional): Type of media (e.g., 'audio'). Defaults to None.
            media_local_path (str, optional): Relative or absolute path to local media file. Defaults to None.

        Returns:
            tuple: (formatted_markdown_content, absolute_file_path, quarter_id)
        """
        paths = self.get_chat_paths(chat_name)

        # Robust timestamp handling to prevent AttributeError or crashes with invalid values
        if isinstance(timestamp, int | float):
            try:
                dt = datetime.fromtimestamp(timestamp / 1000.0)
            except Exception as e:
                logger.warning(f"Invalid numeric timestamp {timestamp}, falling back to current time. Error: {e}")
                dt = datetime.now()
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            logger.warning(f"Unsupported or invalid timestamp type {type(timestamp)} ({timestamp}), falling back to current time.")
            dt = datetime.now()

        filename = self.get_month_filename(dt)
        file_path = os.path.join(paths["chats_dir"], filename)

        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        content = f"### [{time_str}] {sender}\n{text}\n"

        if media_type == "audio" and media_local_path:
            filename_audio = os.path.basename(media_local_path)
            content += f"[Audio](../Audio/{filename_audio})\n"

        # Stable chunk ID — MD5 of (chat_name, sender, time_str).
        # Written as an invisible HTML comment so RAGEngine can extract it
        # for precise vector deletion without MD5-of-content brittleness.
        _chunk_seed = f"{chat_name}_{sender}_{time_str}"
        _chunk_id = f"{hashlib.md5(_chunk_seed.encode()).hexdigest()[:8]}"
        content += f"<!-- chunk_id: {_chunk_id} -->\n"

        content += "\n---\n"

        lock = self.get_lock(file_path)
        with lock:
            with open(file_path, "a", encoding='utf-8') as f:
                f.write(content)

        # Update contact metadata in DB if MetricsEngine is initialized
        try:
            from src.engine.metrics_engine import MetricsEngine
            if MetricsEngine._instance is not None:
                # Clean the body preview text
                snippet_text = text
                if media_type == "audio":
                    snippet_text = "🎙️ Voice Message"
                elif "[Imported Audio Transcription" in snippet_text or "[Live Audio Transcription" in snippet_text:
                    snippet_text = "🎙️ Voice: " + snippet_text.split("Transcription: ")[-1].strip("]")

                snippet_text = snippet_text.replace("\n", " ")
                last_snippet = snippet_text[:35] + "..." if len(snippet_text) > 35 else snippet_text
                last_date = dt.strftime("%Y-%m-%d")

                MetricsEngine().update_contact_metadata(chat_name, last_snippet, last_date)
        except Exception as e:
            logger.error(f"Failed to update contact metadata in DB for {chat_name}: {e}")

        return content, file_path, filename.replace(".md", "")
