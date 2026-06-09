import os
import pytest
import shutil
import json
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

@pytest.fixture
def temp_base_dir(tmp_path):
    d = tmp_path / "chats"
    d.mkdir()
    return str(d)

def test_storage_manager_path_traversal(temp_base_dir):
    sm = StorageManager(base_dir=temp_base_dir)

    # Test case 1: simple traversal
    malicious_name = "../malicious"
    paths = sm.get_chat_paths(malicious_name)

    # It's okay if "malicious" is in the name, as long as it's sanitized and within temp_base_dir
    assert os.path.abspath(paths["chat_root"]).startswith(os.path.abspath(temp_base_dir))
    assert "__malicious" in paths["chat_root"] # sanitized component (.. replaced by __)

    # Test case 2: absolute path traversal
    if os.name != 'nt': # Linux/Mac
        malicious_name = "/tmp/malicious"
    else:
        malicious_name = "C:\\malicious"

    paths = sm.get_chat_paths(malicious_name)
    assert os.path.abspath(paths["chat_root"]).startswith(os.path.abspath(temp_base_dir))

def test_importer_path_traversal(tmp_path, temp_base_dir):
    # Setup a fake export directory
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    inbox_dir = export_dir / "messages" / "inbox"
    inbox_dir.mkdir(parents=True)

    chat_dir = inbox_dir / "test_chat"
    chat_dir.mkdir()

    # Create a message file with a malicious URI
    message_data = {
        "title": "Test Chat",
        "messages": [
            {
                "sender_name": "User",
                "timestamp_ms": 1600000000000,
                "content": "Hello",
                "photos": [
                    {"uri": "../../secret.txt"}
                ]
            }
        ]
    }

    with open(chat_dir / "message_1.json", "w") as f:
        json.dump(message_data, f)

    # Create the "secret" file outside export_dir
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data")

    sm = StorageManager(base_dir=temp_base_dir)
    importer = InstagramDataImporter(sm)

    # Mock media_processor to avoid external calls
    from unittest.mock import patch
    with patch("src.engine.data_importer.media_processor") as mock_mp:
        mock_mp.describe_image.return_value = "mock description"
        importer.import_from_json(str(export_dir))

    # Verify that the secret file was NOT copied
    chat_media_dir = os.path.join(temp_base_dir, "Test Chat", "Media")
    if os.path.exists(chat_media_dir):
        assert not os.path.exists(os.path.join(chat_media_dir, "secret.txt"))
