import json
import os
import shutil
from datetime import datetime

from src.engine.metrics_engine import MetricsEngine
from src.engine.rag_engine import rag_engine
from src.utils.logger import logger
from src.utils.markdown import parse_message_blocks
from src.utils.task_tracker import task_tracker


def is_supported_json_message(msg: dict) -> bool:
    """Determine if a JSON message from export should be imported.
    Returns True for text or audio messages, False for reels or unsupported types.
    """
    # If it has audio files, it's supported
    if "audio_files" in msg:
        return True

    # Check share links for reels
    share = msg.get("share")
    if isinstance(share, dict):
        link = share.get("link", "") or ""
        if "instagram.com/reel/" in link or "instagram.com/reels/" in link:
            return False

    # Check content for reel indicators
    content = msg.get("content", "") or ""
    if "instagram.com/reel/" in content or "instagram.com/reels/" in content:
        return False

    # If it only has photos/videos but no audio, it's a media message (unsupported)
    if ("photos" in msg or "videos" in msg or "gifs" in msg) and "audio_files" not in msg:
        return False

    # If it has text content, it's supported
    if content.strip():
        return True

    return False

class InstagramDataImporter:
    def __init__(self, storage_manager):
        self.sm = storage_manager
        self.metrics_engine = MetricsEngine()

    def _load_existing_signatures(self, chat_name: str) -> set:
        """Reads all existing monthly markdown files for a contact and builds a set of (sender, time_str) signatures."""
        signatures: set[tuple[str, str]] = set()
        paths = self.sm.get_chat_paths(chat_name)
        chats_dir = paths["chats_dir"]

        if not os.path.exists(chats_dir):
            return signatures

        for file in os.listdir(chats_dir):
            if file.endswith(".md"):
                file_path = os.path.join(chats_dir, file)
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                    blocks = parse_message_blocks(content)
                    for block in blocks:
                        lines = block.split("\n")
                        header = lines[0].strip()
                        if header.startswith("### ["):
                            closing_bracket_idx = header.find("]")
                            if closing_bracket_idx != -1:
                                time_str = header[5:closing_bracket_idx]
                                sender = header[closing_bracket_idx + 2:].strip()
                                signatures.add((sender, time_str))
                except Exception as e:
                    logger.error(f"Failed to load signatures from {file_path}: {e}")

        return signatures

    def _resolve_inbox_path(self, export_path: str) -> str:
        """Helper to resolve the actual inbox directory path from any level of user input.
        Handles root exports, your_instagram_activity, messages, inbox, and direct chat folders.
        """
        export_path = export_path.strip()
        if not export_path or not os.path.isdir(export_path):
            return ""

        # Case 1: The path provided is already the inbox folder
        if os.path.basename(export_path.rstrip('/\\')) == 'inbox':
            return export_path

        # Case 2: Standard structures
        standard_paths = [
            os.path.join(export_path, 'messages', 'inbox'),
            os.path.join(export_path, 'your_instagram_activity', 'messages', 'inbox'),
            os.path.join(export_path, 'messages'),
        ]

        for path in standard_paths:
            if os.path.exists(path):
                if os.path.basename(path) == 'messages':
                    inbox_sub = os.path.join(path, 'inbox')
                    if os.path.exists(inbox_sub):
                        return inbox_sub
                return path

        # Case 3: Fallback - check if this directory directly contains chat thread subfolders
        # containing message_*.json files
        try:
            subdirs = [d for d in os.listdir(export_path) if os.path.isdir(os.path.join(export_path, d))]
            for sd in subdirs[:15]:  # limit scan for performance
                sd_path = os.path.join(export_path, sd)
                message_files = [f for f in os.listdir(sd_path) if f.startswith('message_') and f.endswith('.json')]
                if message_files:
                    return export_path
        except Exception:
            pass

        return ""

    def preflight_check(self, export_path: str) -> dict:
        """Performs a fast pre-flight scan of the export directory.
        Returns a dictionary with status, stats, and error messages.
        """
        export_path = export_path.strip()
        if not export_path:
            return {"status": "error", "message": "Path is empty."}

        inbox_path = self._resolve_inbox_path(export_path)
        if not inbox_path:
            return {
                "status": "error",
                "message": f"Inbox directory not found. Please make sure this is a valid unzipped Instagram export folder or the inbox folder itself. Scanned path: {export_path}"
            }

        try:
            chat_folders = [d for d in os.listdir(inbox_path) if os.path.isdir(os.path.join(inbox_path, d))]
            total_threads = len(chat_folders)
            total_json_files = 0

            for folder in chat_folders:
                folder_path = os.path.join(inbox_path, folder)
                message_files = [f for f in os.listdir(folder_path) if f.startswith('message_') and f.endswith('.json')]
                total_json_files += len(message_files)

            return {
                "status": "success",
                "stats": {
                    "total_threads": total_threads,
                    "total_json_files": total_json_files,
                },
                "inbox_path": inbox_path
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to scan folders: {str(e)}"}

    def import_from_json(self, export_path: str, progress_callback=None) -> bool:
        """Parses Instagram export folder.
        Optionally calls progress_callback(current, total, active_chat_name) to report progress.
        Also registers and updates the task in the global task_tracker.
        """
        inbox_path = self._resolve_inbox_path(export_path)
        if not inbox_path:
            logger.error(f"Inbox path not found in {export_path}")
            return False

        # Get list of folders to process
        chat_folders = [d for d in os.listdir(inbox_path) if os.path.isdir(os.path.join(inbox_path, d))]
        total_folders = len(chat_folders)

        if total_folders == 0:
            logger.warning("No chat folders found in inbox directory.")
            return True

        # Register task in global task tracker
        task_id = "import_historical"
        task_tracker.register_task(task_id, "Historical Chat Import", total=total_folders)

        rag_batch = []
        BATCH_SIZE = 50

        try:
            for idx, chat_folder in enumerate(chat_folders):
                # Check for cancellation
                if task_tracker.is_cancelled(task_id):
                    logger.info("Historical import cancelled by user.")
                    task_tracker.fail_task(task_id, "Cancelled by user")
                    return False

                folder_path = os.path.join(inbox_path, chat_folder)
                message_files = sorted([f for f in os.listdir(folder_path) if f.startswith('message_') and f.endswith('.json')])

                existing_sigs = None

                for m_file in message_files:
                    file_path = os.path.join(folder_path, m_file)
                    try:
                        with open(file_path, encoding='utf-8') as f:
                            data = json.load(f)
                    except Exception as e:
                        logger.error(f"Failed to read {file_path}: {e}")
                        continue

                    # Fix encoding issues common in IG exports
                    raw_title = data.get('title', chat_folder)
                    chat_name = raw_title.encode('latin1').decode('utf8') if isinstance(raw_title, str) else str(raw_title)

                    if existing_sigs is None:
                        existing_sigs = self._load_existing_signatures(chat_name)

                    messages = data.get('messages', [])

                    paths = self.sm.get_chat_paths(chat_name)

                    for msg in reversed(messages):
                        # Filter out unsupported messages (reels, etc.)
                        if not is_supported_json_message(msg):
                            continue

                        raw_sender = msg.get('sender_name', 'Unknown')
                        sender = raw_sender.encode('latin1').decode('utf8') if isinstance(raw_sender, str) else str(raw_sender)

                        timestamp = msg.get('timestamp_ms')
                        if not timestamp:
                            continue

                        dt = datetime.fromtimestamp(timestamp / 1000.0)
                        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

                        # Deduplication check
                        if (sender, time_str) in existing_sigs:
                            continue

                        raw_content = msg.get('content', '')
                        text = raw_content.encode('latin1').decode('utf8') if isinstance(raw_content, str) else str(raw_content)

                        media_type = None
                        media_local_path = None

                        # Handle Audio
                        if 'audio_files' in msg:
                            media_type = 'audio'
                            for audio in msg['audio_files']:
                                src_audio = os.path.join(export_path, audio['uri'])
                                if os.path.exists(src_audio):
                                    dst_audio = os.path.join(paths['audio_dir'], os.path.basename(src_audio))
                                    shutil.copy2(src_audio, dst_audio)
                                    media_local_path = dst_audio
                                    text += "\n[Audio Transcription: Processing...]"

                        content, _, month_id = self.sm.save_message(chat_name, sender, text, timestamp, media_type, media_local_path)
                        existing_sigs.add((sender, time_str))

                        # If it was an audio message, enqueue it for parallel transcription
                        if media_type == 'audio' and media_local_path:
                            from src.engine.transcription_queue import transcription_queue
                            transcription_queue.enqueue(chat_name, month_id, sender, time_str, media_local_path)

                        # Record metric in MetricsEngine
                        self.metrics_engine.increment_message(chat_name, timestamp)

                        rag_batch.append((chat_name, month_id, content))
                        if len(rag_batch) >= BATCH_SIZE:
                            rag_engine.add_messages_batch(rag_batch)
                            rag_batch = []

                # Invalidate contacts cache after import
                try:
                    from src.utils.redis_client import invalidate_contacts_cache
                    invalidate_contacts_cache()
                except Exception:
                    pass

                processed = idx + 1
                # Update progress in global task tracker and callback
                task_tracker.update_task(task_id, processed, total_folders)
                if progress_callback:
                    progress_callback(processed, total_folders, chat_name)

            if rag_batch:
                rag_engine.add_messages_batch(rag_batch)

            task_tracker.complete_task(task_id)
            logger.info("Import and Indexing completed successfully.")
            return True

        except Exception as e:
            logger.error(f"Error during import: {e}")
            task_tracker.fail_task(task_id, str(e))
            raise e
