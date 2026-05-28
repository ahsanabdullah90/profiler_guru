import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_vulnerability(tmp_path):
    base_dir = tmp_path / "chats"
    os.makedirs(base_dir)
    sm = StorageManager(base_dir=str(base_dir))

    base_dir_abs = os.path.abspath(str(base_dir))

    # Test case 1: basic traversal
    malicious_chat_name = "../traversal_test"
    paths = sm.get_chat_paths(malicious_chat_name)
    chat_root = os.path.abspath(paths["chat_root"])
    assert chat_root.startswith(base_dir_abs), f"Path traversal detected for {malicious_chat_name}"

    # Test case 2: just ..
    malicious_chat_name = ".."
    paths = sm.get_chat_paths(malicious_chat_name)
    chat_root = os.path.abspath(paths["chat_root"])
    assert chat_root.startswith(base_dir_abs), f"Path traversal detected for {malicious_chat_name}"

    # Test case 3: multiple traversals
    malicious_chat_name = "../../etc/passwd"
    paths = sm.get_chat_paths(malicious_chat_name)
    chat_root = os.path.abspath(paths["chat_root"])
    assert chat_root.startswith(base_dir_abs), f"Path traversal detected for {malicious_chat_name}"

    # Test case 4: null byte (though os.path might handle this)
    malicious_chat_name = "test\0bar"
    paths = sm.get_chat_paths(malicious_chat_name)
    chat_root = os.path.abspath(paths["chat_root"])
    assert chat_root.startswith(base_dir_abs)
