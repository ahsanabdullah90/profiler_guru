import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_protection():
    sm = StorageManager(base_dir="test_chats")

    # These should be sanitized or caught
    malicious_names = [
        "../evil",
        "..\\evil",
        "chat/../../etc/passwd",
        "chat\0hidden"
    ]

    base_dir_abs = os.path.abspath("test_chats")

    for name in malicious_names:
        paths = sm.get_chat_paths(name)
        chat_root_abs = os.path.abspath(paths['chat_root'])

        # Verify it stays within base_dir
        assert chat_root_abs.startswith(base_dir_abs)
        # Verify dangerous characters are gone from the final component
        final_component = os.path.basename(chat_root_abs)
        assert "/" not in final_component
        assert "\\" not in final_component
        assert "\0" not in final_component

def test_storage_manager_sanitization():
    sm = StorageManager(base_dir="test_chats")
    assert sm._sanitize_path_component("hello/world") == "hello_world"
    assert sm._sanitize_path_component("hello\\world") == "hello_world"
    assert sm._sanitize_path_component("hello\0world") == "hello_world"
    # os.path.basename might return empty string for some inputs if they end in /
    # but our _sanitize_path_component replaces / with _ first.
    # Actually, it replaces / with _ first, so it becomes .._.._.._etc_passwd,
    # and os.path.basename of that is the same.
    assert sm._sanitize_path_component("../../../etc/passwd") == ".._.._.._etc_passwd"
