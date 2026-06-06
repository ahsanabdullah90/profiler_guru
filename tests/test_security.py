import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_mitigation(tmp_path):
    # Setup base directory
    base_dir = tmp_path / "chats"
    base_dir.mkdir()

    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name
    malicious_chat = "../evil"

    # This should now stay within base_dir
    paths = sm.get_chat_paths(malicious_chat)
    chat_root = paths["chat_root"]

    # Ensure it's inside base_dir
    assert chat_root.startswith(os.path.abspath(str(base_dir)))
    assert ".._evil" in chat_root

    # Check that evil directory was NOT created outside base_dir
    evil_dir = tmp_path / "evil"
    assert not os.path.exists(evil_dir)

def test_absolute_path_traversal_mitigation(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    malicious_chat = "/tmp/evil"
    paths = sm.get_chat_paths(malicious_chat)
    chat_root = paths["chat_root"]

    assert chat_root.startswith(os.path.abspath(str(base_dir)))
    assert not os.path.exists("/tmp/evil/Chats")
