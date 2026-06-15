import os
import json
import shutil
import pytest
from unittest.mock import MagicMock
import sys

# Mocking modules that might fail to import or require API keys
sys.modules['google'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()
sys.modules['faster_whisper'] = MagicMock()
sys.modules['chromadb'] = MagicMock()

# Mocking media_processor and rag_engine to avoid errors during import
import src.engine.media_processor as mp
mp.describe_image = MagicMock(return_value="mocked description")
mp.transcribe_audio = MagicMock(return_value="mocked transcription")
if not hasattr(sys.modules['src.engine.media_processor'], 'media_processor'):
    sys.modules['src.engine.media_processor'].media_processor = mp

import src.engine.rag_engine as re
re.rag_engine = MagicMock()

from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

@pytest.fixture
def temp_dirs(tmp_path):
    export_dir = tmp_path / "export"
    chats_dir = tmp_path / "chats"
    export_dir.mkdir()
    chats_dir.mkdir()
    return export_dir, chats_dir

def test_chat_name_path_traversal(temp_dirs):
    export_dir, chats_dir = temp_dirs
    sm = StorageManager(base_dir=str(chats_dir))

    # Malicious chat name attempting to escape chats_dir
    malicious_chat_name = "../attacker_dir"

    # If vulnerable, this will create 'attacker_dir' outside 'chats_dir'
    paths = sm.get_chat_paths(malicious_chat_name)

    # The actual path should be within chats_dir
    assert os.path.abspath(paths['chat_root']).startswith(os.path.abspath(str(chats_dir)))

def test_importer_media_path_traversal(temp_dirs, tmp_path):
    export_dir, chats_dir = temp_dirs

    # Create a secret file outside export_dir
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data")

    # Create malicious JSON export
    inbox_path = export_dir / "messages" / "inbox"
    chat_dir = inbox_path / "chat1"
    chat_dir.mkdir(parents=True)

    # URI attempting to access secret.txt via traversal
    # export_dir is at tmp_path/export
    # secret_file is at tmp_path/secret.txt
    # relative path from export_dir to secret_file is ../secret.txt

    malicious_data = {
        "title": "Normal Chat",
        "messages": [
            {
                "sender_name": "Attacker",
                "timestamp_ms": 1600000000000,
                "content": "Look at this",
                "photos": [{"uri": "../secret.txt"}]
            }
        ]
    }

    with open(chat_dir / "message_1.json", "w") as f:
        json.dump(malicious_data, f)

    sm = StorageManager(base_dir=str(chats_dir))
    importer = InstagramDataImporter(sm)

    importer.import_from_json(str(export_dir))

    # Check if secret.txt was copied
    copied_secret = chats_dir / "Normal Chat" / "Media" / "secret.txt"
    assert not os.path.exists(copied_secret), "Vulnerability: secret.txt was copied via path traversal!"

def test_storage_manager_sanitization():
    sm = StorageManager(base_dir="test_chats")

    # Test various malicious inputs
    unsafe_names = [
        "../evil",
        "../../evil",
        "/etc/passwd",
        "C:\\Windows",
        "chat\0name",
        "..",
        "."
    ]

    for name in unsafe_names:
        paths = sm.get_chat_paths(name)
        # Should not be able to escape test_chats
        assert os.path.abspath(paths['chat_root']).startswith(os.path.abspath("test_chats"))
        # Should not be exactly test_chats (if it resolved to the base dir itself)
        assert os.path.abspath(paths['chat_root']) != os.path.abspath("test_chats")
