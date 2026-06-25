import os
import queue
import time
import threading
from src.utils.config import config
from src.utils.logger import logger
from src.storage.storage_manager import StorageManager
from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine

class TranscriptionQueue:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TranscriptionQueue, cls).__new__(cls)
                cls._instance._init()
            return cls._instance

    def _init(self):
        self.queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        logger.info("Transcription queue background worker thread started.")

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
                
                # 1. Transcribe the audio file
                try:
                    transcription = media_processor.transcribe_audio(audio_path)
                except Exception as e:
                    logger.error(f"Failed to transcribe {audio_path}: {e}")
                    transcription = "Transcription failed."

                # 2. Update the markdown file in-place thread-safely
                sm = StorageManager(config.CHATS_DIR)
                paths = sm.get_chat_paths(chat_name)
                file_path = os.path.join(paths["chats_dir"], f"{month_id}.md")
                
                if os.path.exists(file_path):
                    with sm.get_lock(file_path):
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                content = f.read()
                            
                            # Find the specific message block and update the placeholder
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
                                        # Replace placeholder with actual transcription
                                        replacement = f"[Imported Audio Transcription: {transcription}]"
                                        blocks[i] = block.replace(placeholder, replacement)
                                        new_block = blocks[i]
                                        break
                            
                            if old_block and new_block:
                                # Reconstruct content and write back
                                new_content = "---".join(blocks)
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write(new_content)
                                logger.info(f"Successfully updated markdown file in-place for {chat_name} - {sender} [{time_str}]")
                                
                                # 3. Update RAG Vector database in-place (delete old vector chunks and add the new one)
                                try:
                                    rag_engine.update_transcribed_message(chat_name, month_id, old_block, new_block)
                                    logger.info(f"Successfully re-indexed transcribed chunk in ChromaDB for {chat_name}")
                                except Exception as e:
                                    logger.error(f"Failed to update RAG vector store for {chat_name}: {e}")
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
