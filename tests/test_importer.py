import os
import json
import pytest
from src.engine.data_importer import InstagramDataImporter

def test_import_from_json(tmp_path, temp_storage):
    # Setup mock Instagram export structure
    export_path = tmp_path / "instagram_export"
    messages_path = export_path / "messages" / "inbox" / "alice_123"
    messages_path.mkdir(parents=True)

    message_data = {
        "title": "Alice",
        "messages": [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1700000000000,
                "content": "Hello!"
            }
        ]
    }

    # We need to simulate the latin1/utf8 encoding issue if we want to be thorough,
    # but the code does .encode('latin1').decode('utf8').
    # Let's write it in a way that the decoder won't fail.
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump(message_data, f)

    importer = InstagramDataImporter(temp_storage)
    success = importer.import_from_json(str(export_path))

    assert success

    # Check if files were created in storage
    chat_paths = temp_storage.get_chat_paths("Alice")
    assert os.path.exists(chat_paths["chats_dir"])
    files = os.listdir(chat_paths["chats_dir"])
    assert len(files) > 0

def test_preflight_check(tmp_path, temp_storage):
    importer = InstagramDataImporter(temp_storage)
    
    # Test empty path
    res = importer.preflight_check("")
    assert res["status"] == "error"
    assert "empty" in res["message"].lower()

    # Test non-existent path
    res = importer.preflight_check(str(tmp_path / "non_existent"))
    assert res["status"] == "error"
    assert "not found" in res["message"].lower()

    # Setup valid structure
    export_path = tmp_path / "instagram_export_preflight"
    messages_path = export_path / "your_instagram_activity" / "messages" / "inbox" / "bob_456"
    messages_path.mkdir(parents=True)
    
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump({"title": "Bob", "messages": []}, f)
        
    res = importer.preflight_check(str(export_path))
    assert res["status"] == "success"
    assert res["stats"]["total_threads"] == 1
    assert res["stats"]["total_json_files"] == 1

    # Test direct inbox folder validation (fixes folder sync bug)
    inbox_dir_path = export_path / "your_instagram_activity" / "messages" / "inbox"
    res_direct = importer.preflight_check(str(inbox_dir_path))
    assert res_direct["status"] == "success"
    assert res_direct["stats"]["total_threads"] == 1
    assert res_direct["stats"]["total_json_files"] == 1

def test_import_with_progress_callback(tmp_path, temp_storage):
    export_path = tmp_path / "instagram_export_callback"
    messages_path = export_path / "messages" / "inbox" / "charlie_789"
    messages_path.mkdir(parents=True)

    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump({"title": "Charlie", "messages": [{"sender_name": "Charlie", "timestamp_ms": 1700000000000, "content": "Hi"}]}, f)

    importer = InstagramDataImporter(temp_storage)
    
    progress_calls = []
    def progress_cb(current, total, active_chat):
        progress_calls.append((current, total, active_chat))

    success = importer.import_from_json(str(export_path), progress_callback=progress_cb)
    assert success
    assert len(progress_calls) == 1
    assert progress_calls[0] == (1, 1, "Charlie")
