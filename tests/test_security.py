import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_vulnerability(tmp_path):
    # Base directory for chats
    base_dir = tmp_path / "chats"
    base_dir.mkdir()

    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name attempting to escape the base directory
    malicious_chat_name = "../traversal_test"

    # This should ideally NOT create a directory outside base_dir
    paths = sm.get_chat_paths(malicious_chat_name)

    chat_root = os.path.abspath(paths["chat_root"])
    base_dir_abs = os.path.abspath(str(base_dir))

    # Verify if it escaped
    assert chat_root.startswith(base_dir_abs), f"Path traversal detected! {chat_root} is outside {base_dir_abs}"

def test_path_traversal_with_null_byte(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    malicious_chat_name = "normal_chat\0/../../etc"
    paths = sm.get_chat_paths(malicious_chat_name)

    chat_root = os.path.abspath(paths["chat_root"])
    base_dir_abs = os.path.abspath(str(base_dir))

    assert chat_root.startswith(base_dir_abs)
