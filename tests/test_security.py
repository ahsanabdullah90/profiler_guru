import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

def test_storage_manager_path_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name
    malicious_chat = "../external_dir"
    paths = sm.get_chat_paths(malicious_chat)

    # The chat_root should ideally be within base_dir
    # We use os.path.join(base_dir, '') to ensure a trailing separator for prefix matching
    base_dir_abs = os.path.abspath(str(base_dir)) + os.sep
    assert os.path.abspath(paths["chat_root"]).startswith(base_dir_abs)

def test_importer_path_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    # Secret file outside export_dir
    # Place it one level above export_dir
    secret_file = tmp_path / "sensitive.txt"
    secret_file.write_text("SECRET")

    inbox_path = export_dir / "messages" / "inbox" / "attacker_chat"
    inbox_path.mkdir(parents=True)

    malicious_data = {
        "title": "Attacker",
        "messages": [
            {
                "sender_name": "Attacker",
                "timestamp_ms": 1700000000000,
                "content": "test",
                "photos": [{"uri": "../sensitive.txt"}]
            }
        ]
    }

    with open(inbox_path / "message_1.json", "w") as f:
        json.dump(malicious_data, f)

    sm = StorageManager(base_dir=str(base_dir))

    with patch('src.engine.media_processor.describe_image', return_value="a photo"):
        with patch('src.engine.rag_engine.rag_engine.add_messages_to_index'):
            importer = InstagramDataImporter(sm)
            importer.import_from_json(str(export_dir))

    # Check if secret was copied
    # The importer uses the title 'Attacker' for the chat directory
    stolen_file = base_dir / "Attacker" / "Media" / "sensitive.txt"
    assert not os.path.exists(stolen_file), "Vulnerability: file was stolen via path traversal!"
