import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_prevention(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    malicious_names = [
        "../evil",
        "..\\evil",
        "/etc/passwd",
        "\0secret",
        "chat/../traversal",
        "C:\\Windows\\System32"
    ]

    for name in malicious_names:
        paths = sm.get_chat_paths(name)
        chat_root = paths["chat_root"]

        # Ensure it's inside base_dir
        assert os.path.abspath(chat_root).startswith(os.path.abspath(str(base_dir)))

        # Ensure it doesn't contain traversal characters
        # We allow double underscores or other replacements, but not ".." as a directory component
        normalized_name = os.path.basename(chat_root)
        # os.path.basename after our sanitization should not be ".." or start with "../"
        assert normalized_name not in [".", ".."]
        assert not normalized_name.startswith("../")
        assert not normalized_name.startswith("..\\")

def test_safe_chat_name_creation(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Check that it still works for normal names
    paths = sm.get_chat_paths("john_doe")
    assert "john_doe" in paths["chat_root"]
    assert os.path.exists(paths["chats_dir"])
