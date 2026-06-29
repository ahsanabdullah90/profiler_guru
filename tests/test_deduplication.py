import os
import pytest
import shutil
import json
from pathlib import Path
from src.engine.data_importer import InstagramDataImporter
from src.storage.storage_manager import StorageManager
from src.engine.metrics_engine import MetricsEngine
from scripts.self_healing import deduplicate_all_data
from src.utils.config import config

def test_historical_import_deduplication(tmp_path, monkeypatch):
    # 1. Setup temporary directories
    test_chats_dir = tmp_path / "chats"
    test_db_path = tmp_path / "psych_profiles.db"
    
    # Patch config paths
    monkeypatch.setattr(config, "CHATS_DIR", test_chats_dir)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    
    # Re-initialize MetricsEngine singleton for test
    MetricsEngine._instance = None
    metrics_engine = MetricsEngine(db_path=test_db_path)
    
    storage_manager = StorageManager(str(test_chats_dir))
    importer = InstagramDataImporter(storage_manager)
    
    # Create a mock Instagram export directory
    export_dir = tmp_path / "mock_export"
    inbox_dir = export_dir / "messages" / "inbox" / "testcontact_123"
    inbox_dir.mkdir(parents=True)
    
    import time
    now_ms = int(time.time() * 1000.0)

    # Write message_1.json containing duplicate messages
    messages_data = {
        "title": "Test Contact",
        "messages": [
            {
                "sender_name": "Test Contact",
                "timestamp_ms": now_ms,
                "content": "Hello! Duplicate message content here."
            },
            {
                "sender_name": "Test Contact",
                "timestamp_ms": now_ms,  # Same timestamp
                "content": "Hello! Duplicate message content here."  # Duplicate
            },
            {
                "sender_name": "Test Contact",
                "timestamp_ms": now_ms - 60000,  # Different timestamp
                "content": "This is a unique message."
            }
        ]
    }
    
    with open(inbox_dir / "message_1.json", "w", encoding="utf-8") as f:
        json.dump(messages_data, f)
        
    # Run the import
    success = importer.import_from_json(str(export_dir))
    assert success is True
    
    # Verify that only 2 messages were written (1 duplicate skipped)
    paths = storage_manager.get_chat_paths("Test Contact")
    chats_dir = Path(paths["chats_dir"])
    md_files = list(chats_dir.glob("*.md"))
    assert len(md_files) == 1
    
    with open(md_files[0], "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check that "Duplicate message content" appears only once
    assert content.count("Duplicate message content") == 1
    assert content.count("unique message") == 1
    
    # Verify SQLite metrics: only 2 messages should be counted (directly query DB to be timezone-independent)
    cur = metrics_engine.conn.cursor()
    cur.execute("SELECT SUM(message_count) FROM connection_metrics WHERE chat_name = ?;", ("Test Contact",))
    total_msgs = cur.fetchone()[0] or 0
    assert total_msgs == 2

def test_self_healing_deduplication(tmp_path, monkeypatch):
    # 1. Setup temporary directories
    test_chats_dir = tmp_path / "chats"
    test_db_path = tmp_path / "psych_profiles.db"
    
    # Patch config paths
    monkeypatch.setattr(config, "CHATS_DIR", test_chats_dir)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    
    # Re-initialize MetricsEngine singleton for test
    MetricsEngine._instance = None
    metrics_engine = MetricsEngine(db_path=test_db_path)
    
    storage_manager = StorageManager(str(test_chats_dir))
    
    # 2. Manually create a duplicated markdown file
    paths = storage_manager.get_chat_paths("Duplicated Contact")
    file_path = Path(paths["chats_dir"]) / "2026_06.md"
    
    duplicate_content = (
        "### [2026-06-24 12:00:00] Duplicated Contact\nHello there!\n\n---\n"
        "### [2026-06-24 12:00:00] Duplicated Contact\nHello there!\n\n---\n"  # Duplicate
        "### [2026-06-24 12:05:00] Duplicated Contact\nThis is unique.\n\n---\n"
    )
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(duplicate_content)
        
    # Populate bloated metrics in database
    metrics_engine.increment_message("Duplicated Contact", "2026-06-24")
    metrics_engine.increment_message("Duplicated Contact", "2026-06-24")
    metrics_engine.increment_message("Duplicated Contact", "2026-06-24")  # Total 3
    
    stats_before = metrics_engine.get_daily_stats("Duplicated Contact", days=30)
    assert sum(s[1] for s in stats_before) == 3
    
    # 3. Run self-healing deduplication
    deduplicate_all_data()
    
    # 4. Verify markdown file has been cleaned
    with open(file_path, "r", encoding="utf-8") as f:
        cleaned_content = f.read()
        
    assert cleaned_content.count("Hello there!") == 1
    assert cleaned_content.count("unique") == 1
    
    # 5. Verify SQLite metrics have been repaired (should be 2 instead of 3)
    stats_after = metrics_engine.get_daily_stats("Duplicated Contact", days=30)
    assert sum(s[1] for s in stats_after) == 2
