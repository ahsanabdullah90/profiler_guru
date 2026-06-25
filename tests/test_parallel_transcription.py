import os
import pytest
import time
import shutil
from pathlib import Path
from datetime import datetime
from src.engine.transcription_queue import transcription_queue
from src.storage.storage_manager import StorageManager
from src.engine.media_processor import media_processor
from src.engine.rag_engine import rag_engine
from src.utils.config import config

def test_parallel_transcription_pipeline(tmp_path, monkeypatch):
    # 1. Setup temporary directories
    test_chats_dir = tmp_path / "chats"
    monkeypatch.setattr(config, "CHATS_DIR", test_chats_dir)
    
    # 2. Mock transcribe_audio to return a fixed text instantly
    monkeypatch.setattr(media_processor, "transcribe_audio", lambda p: "This is a mock transcribed voice note.")
    
    # Mock RAGEngine.update_transcribed_message to track calls
    updated_calls = []
    monkeypatch.setattr(rag_engine, "update_transcribed_message", lambda c, m, o, n: updated_calls.append((c, m, o, n)))
    
    storage_manager = StorageManager(str(test_chats_dir))
    
    # 3. Create a chat log with a placeholder
    chat_name = "Parallel Voice Contact"
    sender = "Parallel Voice Contact"
    timestamp = 1782310800000  # Epoch for 2026-06-24 14:00:00 UTC
    dt = datetime.fromtimestamp(timestamp / 1000.0)
    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
    month_id = f"{dt.year}_{dt.month:02d}"
    
    placeholder_text = "🎙️ Voice Message\n[Audio Transcription: Processing...]"
    
    content, file_path, resolved_month = storage_manager.save_message(
        chat_name=chat_name,
        sender=sender,
        text=placeholder_text,
        timestamp=timestamp,
        media_type="audio",
        media_local_path="mock_audio.mp3"
    )
    
    # Verify placeholder is in the file
    with open(file_path, "r", encoding="utf-8") as f:
        log_content_before = f.read()
    assert "[Audio Transcription: Processing...]" in log_content_before
    
    # 4. Enqueue the transcription task
    transcription_queue.enqueue(
        chat_name=chat_name,
        month_id=month_id,
        sender=sender,
        time_str=time_str,
        audio_path="mock_audio.mp3"
    )
    
    # 5. Wait for the background worker to process the task (it runs immediately)
    # We poll the queue until it is empty (using join with a timeout)
    queue_completed = False
    for _ in range(50):  # 5 seconds max timeout
        if transcription_queue.queue.empty():
            queue_completed = True
            break
        time.sleep(0.1)
        
    assert queue_completed is True
    
    # Wait an extra fraction of a second for file write to finish
    time.sleep(0.2)
    
    # 6. Verify markdown file has been updated in-place
    with open(file_path, "r", encoding="utf-8") as f:
        log_content_after = f.read()
        
    assert "[Audio Transcription: Processing...]" not in log_content_after
    assert "[Imported Audio Transcription: This is a mock transcribed voice note.]" in log_content_after
    assert "mock_audio.mp3" in log_content_after
    
    # 7. Verify RAG re-indexing was triggered
    assert len(updated_calls) == 1
    c, m, o, n = updated_calls[0]
    assert c == chat_name
    assert m == month_id
    assert "[Audio Transcription: Processing...]" in o
    assert "This is a mock transcribed voice note." in n
