import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_vulnerability(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Malicious chat name
    malicious_chat_name = "../../traversal_target"

    # Before fix, this would likely create a directory outside base_dir
    paths = sm.get_chat_paths(malicious_chat_name)

    chat_root_abs = os.path.abspath(paths["chat_root"])
    base_dir_abs = os.path.abspath(str(base_dir))

    # It should be inside base_dir_abs
    assert chat_root_abs.startswith(base_dir_abs), f"{chat_root_abs} is outside {base_dir_abs}"

def test_chat_name_sanitization(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Test various malicious names
    malicious_names = [
        "../test",
        "/absolute/path",
        "nested/../../path",
        "CON", # Windows reserved
        "space in name",
        "null\0byte"
    ]

    for name in malicious_names:
        paths = sm.get_chat_paths(name)
        chat_root_abs = os.path.abspath(paths["chat_root"])
        base_dir_abs = os.path.abspath(str(base_dir))

        assert chat_root_abs.startswith(base_dir_abs), f"Failed for {name}: {chat_root_abs} is outside {base_dir_abs}"
        # Also ensure the resulting name is somewhat sane and doesn't contain traversal
        assert ".." not in paths["chat_root"]
