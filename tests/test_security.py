import os
import pytest
from src.storage.storage_manager import StorageManager

def test_storage_manager_path_traversal(tmp_path):
    storage = StorageManager(base_dir=str(tmp_path))

    # Test with a malicious chat name attempting to go up one level
    malicious_name = "../malicious"
    paths = storage.get_chat_paths(malicious_name)

    # The actual directory should be under the base_dir and not outside it
    # With our fix, it should be .._malicious or malicious depending on how we handle it.
    # Currently we replace / with _
    assert os.path.basename(paths["chat_root"]) == ".._malicious"
    assert paths["chat_root"] == os.path.join(str(tmp_path), ".._malicious")
    assert os.path.exists(paths["chat_root"])

def test_storage_manager_windows_traversal(tmp_path):
    storage = StorageManager(base_dir=str(tmp_path))

    malicious_name = "..\\malicious"
    paths = storage.get_chat_paths(malicious_name)

    assert os.path.basename(paths["chat_root"]) == ".._malicious"
    assert paths["chat_root"] == os.path.join(str(tmp_path), ".._malicious")
    assert os.path.exists(paths["chat_root"])

def test_storage_manager_dangerous_names(tmp_path):
    storage = StorageManager(base_dir=str(tmp_path))

    dangerous_names = ["..", ".", "/"]
    for name in dangerous_names:
        paths = storage.get_chat_paths(name)
        assert os.path.basename(paths["chat_root"]) == "Unknown_Chat"
        assert paths["chat_root"] == os.path.join(str(tmp_path), "Unknown_Chat")
