import os
import pytest
import shutil
import json
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

def test_storage_manager_path_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    sm = StorageManager(str(base_dir))

    # Attempt traversal
    traversal_name = "../../traversal_test"
    paths = sm.get_chat_paths(traversal_name)

    # Check if the chat_root is outside base_dir
    assert os.path.abspath(paths['chat_root']).startswith(os.path.abspath(str(base_dir)))

def test_importer_path_traversal(tmp_path):
    # Setup storage
    base_dir = tmp_path / "chats"
    sm = StorageManager(str(base_dir))
    importer = InstagramDataImporter(sm)

    # Setup malicious export
    export_dir = tmp_path / "export"
    export_dir.mkdir()

    # Create a sensitive file to "steal"
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("this is a secret")

    inbox_dir = export_dir / "messages" / "inbox" / "malicious_chat"
    inbox_dir.mkdir(parents=True)

    # Malicious JSON pointing to the secret file outside export_dir
    # Note: we use a relative path that goes up from export_dir
    relative_secret_path = os.path.relpath(str(secret_file), str(export_dir))

    message_data = {
        "title": "Malicious Chat",
        "messages": [
            {
                "sender_name": "Attacker",
                "timestamp_ms": 1600000000000,
                "content": "Look at this file",
                "photos": [{"uri": relative_secret_path}]
            }
        ]
    }

    with open(inbox_dir / "message_1.json", "w") as f:
        json.dump(message_data, f)

    # Run importer
    importer.import_from_json(str(export_dir))

    # Check if secret file was copied into chats
    chat_media_dir = base_dir / "Malicious Chat" / "Media"
    stolen_file = chat_media_dir / "secret.txt"

    assert not stolen_file.exists(), "Path traversal successful! Secret file was leaked."
