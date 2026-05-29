import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_mitigation(tmp_path):
    base_dir = tmp_path / "chats"
    os.makedirs(base_dir)
    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name attempt
    malicious_chat_name = "../external_dir"

    paths = sm.get_chat_paths(malicious_chat_name)

    # The fix should have sanitized "../external_dir" to "external_dir" (via basename)
    # OR if it was "evil/path" -> "evil_path"

    chat_root = paths["chat_root"]

    # Verify it's within base_dir
    assert os.path.commonpath([os.path.abspath(base_dir)]) == os.path.commonpath([os.path.abspath(base_dir), os.path.abspath(chat_root)])

    # In our specific implementation:
    # "../external_dir" -> replace "/" with "_" -> ".._external_dir" -> basename -> ".._external_dir"
    # Wait, basename of ".._external_dir" is ".._external_dir".
    # os.path.join(base_dir, ".._external_dir") is inside base_dir.

    assert os.path.basename(chat_root) == ".._external_dir"
    assert os.path.exists(chat_root)
    assert os.path.dirname(chat_root) == str(os.path.abspath(base_dir))

def test_null_byte_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    os.makedirs(base_dir)
    sm = StorageManager(base_dir=str(base_dir))

    malicious_chat_name = "normal\0evil"
    paths = sm.get_chat_paths(malicious_chat_name)

    assert "\0" not in os.path.basename(paths["chat_root"])
    assert "normal_evil" in os.path.basename(paths["chat_root"])
