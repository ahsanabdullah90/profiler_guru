import os
import json
import shutil
from datetime import datetime
from src.storage.storage_manager import StorageManager
from src.utils.logger import logger
from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine

class InstagramDataImporter:
    def __init__(self, storage_manager):
        self.sm = storage_manager
        self.batch_size = 50

    def import_from_json(self, export_path):
        """
        Parses Instagram export folder and indexes messages in batches.
        """
        inbox_path = os.path.join(export_path, 'messages', 'inbox')
        if not os.path.exists(inbox_path):
            # Try alternative export structure
            inbox_path = os.path.join(export_path, 'your_instagram_activity', 'messages', 'inbox')

        if not os.path.exists(inbox_path):
            logger.error(f"Inbox path not found in {export_path}")
            return False

        # Buffer for batch indexing: {(chat_name, quarter_id): [message_contents]}
        rag_buffer = {}

        def flush_batch(chat, quarter, force=False):
            """Flushes a specific chat/quarter batch if it meets the size threshold or force is True."""
            messages = rag_buffer.get((chat, quarter), [])
            if messages and (force or len(messages) >= self.batch_size):
                rag_engine.add_messages_to_index(chat, quarter, messages)
                rag_buffer[(chat, quarter)] = []

        def flush_all():
            """Flushes all remaining messages in the buffer."""
            for (chat, quarter), messages in rag_buffer.items():
                if messages:
                    rag_engine.add_messages_to_index(chat, quarter, messages)
            rag_buffer.clear()

        for chat_folder in os.listdir(inbox_path):
            folder_path = os.path.join(inbox_path, chat_folder)
            if not os.path.isdir(folder_path):
                continue

            message_files = sorted([f for f in os.listdir(folder_path) if f.startswith('message_') and f.endswith('.json')])

            for m_file in message_files:
                file_path = os.path.join(folder_path, m_file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to read {file_path}: {e}")
                    continue

                # Fix encoding issues common in IG exports
                raw_title = data.get('title', chat_folder)
                chat_name = raw_title.encode('latin1').decode('utf8') if isinstance(raw_title, str) else str(raw_title)

                messages = data.get('messages', [])

                for msg in reversed(messages):
                    raw_sender = msg.get('sender_name', 'Unknown')
                    sender = raw_sender.encode('latin1').decode('utf8') if isinstance(raw_sender, str) else str(raw_sender)

                    timestamp = msg.get('timestamp_ms')

                    raw_content = msg.get('content', '')
                    text = raw_content.encode('latin1').decode('utf8') if isinstance(raw_content, str) else str(raw_content)

                    media_type = None
                    media_local_path = None

                    paths = self.sm.get_chat_paths(chat_name)

                    # Handle Photos
                    if 'photos' in msg:
                        media_type = 'image'
                        for photo in msg['photos']:
                            src_photo = os.path.join(export_path, photo['uri'])
                            if os.path.exists(src_photo):
                                dst_photo = os.path.join(paths['media_dir'], os.path.basename(src_photo))
                                shutil.copy2(src_photo, dst_photo)
                                media_local_path = dst_photo
                                # Add description to text for RAG
                                description = media_processor.describe_image(dst_photo)
                                text += f"\n[Imported Image Description: {description}]"

                    # Handle Audio
                    if 'audio_files' in msg:
                        media_type = 'audio'
                        for audio in msg['audio_files']:
                            src_audio = os.path.join(export_path, audio['uri'])
                            if os.path.exists(src_audio):
                                dst_audio = os.path.join(paths['audio_dir'], os.path.basename(src_audio))
                                shutil.copy2(src_audio, dst_audio)
                                media_local_path = dst_audio
                                # Transcribe
                                transcription = media_processor.transcribe_audio(dst_audio)
                                text += f"\n[Imported Audio Transcription: {transcription}]"

                    content, _, quarter_id = self.sm.save_message(chat_name, sender, text, timestamp, media_type, media_local_path)

                    # Buffer message for batch indexing
                    key = (chat_name, quarter_id)
                    if key not in rag_buffer:
                        rag_buffer[key] = []
                    rag_buffer[key].append(content)

                    # Flush specifically for this key if batch size reached (O(1) check)
                    flush_batch(chat_name, quarter_id)

        # Final flush to ensure all remaining messages are indexed
        flush_all()

        logger.info("Import and Indexing completed successfully.")
        return True
