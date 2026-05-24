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

    def import_from_json(self, export_path):
        """
        Parses Instagram export.
        Expected path: [export_path]/messages/inbox/
        """
        inbox_path = os.path.join(export_path, 'messages', 'inbox')
        if not os.path.exists(inbox_path):
            logger.error(f"Inbox path not found: {inbox_path}")
            return False

        for chat_folder in os.listdir(inbox_path):
            folder_path = os.path.join(inbox_path, chat_folder)
            if not os.path.isdir(folder_path):
                continue

            # Find all message_*.json files
            message_files = [f for f in os.listdir(folder_path) if f.startswith('message_') and f.endswith('.json')]

            for m_file in message_files:
                file_path = os.path.join(folder_path, m_file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                chat_name = data.get('title', chat_folder).encode('latin1').decode('utf8')
                messages = data.get('messages', [])

                for msg in reversed(messages):
                    sender = msg.get('sender_name', 'Unknown').encode('latin1').decode('utf8')
                    timestamp = msg.get('timestamp_ms')
                    text = msg.get('content', '').encode('latin1').decode('utf8') if msg.get('content') else ''

                    media_type = None
                    media_local_path = None

                    paths = self.sm.get_chat_paths(chat_name)

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
                                text += f"\n[Image Description: {description}]"

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
                                text += f"\n[Audio Transcription: {transcription}]"

                    content, _, quarter_id = self.sm.save_message(chat_name, sender, text, timestamp, media_type, media_local_path)
                    # Auto Indexing
                    rag_engine.add_messages_to_index(chat_name, quarter_id, content)

        logger.info("Import and Indexing completed successfully.")
        return True
