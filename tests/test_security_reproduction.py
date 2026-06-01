import os
import pytest
from src.storage.storage_manager import StorageManager

def test_path_traversal_protection(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Attempt path traversal
    malicious_chat_name = "../../evil_dir"

    # This should now be sanitized and remain within base_dir
    paths = sm.get_chat_paths(malicious_chat_name)

    chat_root = paths["chat_root"]

    base_dir_abs = os.path.abspath(str(base_dir))
    chat_root_abs = os.path.abspath(chat_root)

    print(f"Base dir: {base_dir_abs}")
    print(f"Chat root: {chat_root_abs}")

    # Check if the created directory is INSIDE base_dir
    assert chat_root_abs.startswith(base_dir_abs)
    assert "evil_dir" in chat_root_abs
    assert ".." not in os.path.basename(chat_root_abs) or ".." in chat_root_abs # depending on how it was sanitized

def test_null_byte_traversal(tmp_path):
    base_dir = tmp_path / "chats"
    base_dir.mkdir()
    sm = StorageManager(base_dir=str(base_dir))

    # Null byte injection
    malicious_name = "normal\0../../evil"
    paths = sm.get_chat_paths(malicious_name)
    chat_root_abs = os.path.abspath(paths["chat_root"])

    assert os.path.abspath(str(base_dir)) in chat_root_abs
    assert "\0" not in chat_root_abs

if __name__ == "__main__":
    import tempfile
    import shutil
    tmp = tempfile.mkdtemp()
    try:
        test_path_traversal_protection(os.path.join(tmp, "root"))
    finally:
        shutil.rmtree(tmp)
