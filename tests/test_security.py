import os
import pytest
import shutil
import json
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

def test_storage_manager_path_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name
    malicious_chat = "../evil_dir"

    # The fix should either sanitize it OR raise an error if it's still malicious.
    # In my implementation, it sanitizes using basename, making it "evil_dir"
    paths = sm.get_chat_paths(malicious_chat)

    # Check if it escaped base_dir
    chat_root_abs = os.path.abspath(paths['chat_root'])
    base_dir_abs = os.path.abspath(str(base_dir))

    # It should NOT be outside base_dir_abs
    assert chat_root_abs.startswith(base_dir_abs + os.sep)
    assert "evil_dir" in chat_root_abs
    assert ".." not in paths['chat_root']

def test_storage_manager_path_traversal_absolute(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Absolute malicious path
    malicious_chat = "/tmp/evil_dir"

    paths = sm.get_chat_paths(malicious_chat)
    chat_root_abs = os.path.abspath(paths['chat_root'])
    base_dir_abs = os.path.abspath(str(base_dir))

    assert chat_root_abs.startswith(base_dir_abs + os.sep)

def test_data_importer_path_traversal(tmp_path, monkeypatch):
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    # Create fake message JSON with malicious URI
    inbox_dir = export_dir / "messages" / "inbox" / "malicious_chat"
    inbox_dir.mkdir(parents=True)

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data")

    # Relative path from inbox_dir/message_1.json to secret.txt
    # inbox_dir is export/messages/inbox/malicious_chat
    # export is tmp_path/export
    # secret.txt is tmp_path/secret.txt
    # photo['uri'] is relative to export_dir
    malicious_uri = "../secret.txt"

    message_data = {
        "title": "Malicious Chat",
        "messages": [
            {
                "sender_name": "Attacker",
                "timestamp_ms": 1700000000000,
                "content": "Look at this file",
                "photos": [{"uri": malicious_uri}]
            }
        ]
    }

    with open(inbox_dir / "message_1.json", "w") as f:
        json.dump(message_data, f)

    chats_dir = tmp_path / "chats"
    chats_dir.mkdir()
    sm = StorageManager(base_dir=str(chats_dir))
    importer = InstagramDataImporter(sm)

    # Mock media_processor to avoid actual processing
    monkeypatch.setattr("src.engine.data_importer.media_processor.describe_image", lambda x: "description")
    monkeypatch.setattr("src.engine.data_importer.rag_engine.add_messages_to_index", lambda *args: None)

    # This should fail or be blocked if we have security checks
    # In vulnerable state, it might copy secret_file to chats_dir/Malicious Chat/Media/secret.txt

    # Verify src exists
    src_photo = os.path.join(str(export_dir), malicious_uri)
    assert os.path.exists(src_photo)

    importer.import_from_json(str(export_dir))

    dst_secret = chats_dir / "Malicious Chat" / "Media" / "secret.txt"
    # If it exists, traversal was successful
    assert not dst_secret.exists()
