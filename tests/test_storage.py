import os
from src.storage.storage_manager import StorageManager

def test_storage_manager_init(tmp_path):
    base_dir = tmp_path / "chats"
    sm = StorageManager(base_dir=str(base_dir))
    assert os.path.exists(base_dir)

def test_get_chat_paths(temp_storage):
    paths = temp_storage.get_chat_paths("test_user")
    assert os.path.exists(paths["chat_root"])
    assert os.path.exists(paths["chats_dir"])
    assert os.path.exists(paths["media_dir"])
    assert os.path.exists(paths["audio_dir"])

def test_save_message(temp_storage):
    chat_name = "test_user"
    sender = "Alice"
    text = "Hello!"
    timestamp = 1700000000000 # 2023-11-14

    content, file_path, quarter_id = temp_storage.save_message(chat_name, sender, text, timestamp)

    assert os.path.exists(file_path)
    assert "2023_Q4" in file_path
    assert "Alice" in content
    assert "Hello!" in content

    with open(file_path, "r") as f:
        saved_content = f.read()
        assert "Alice" in saved_content
        assert "Hello!" in saved_content

def test_path_traversal_fixed(temp_storage):
    # Attempt to use a chat_name that traverses out of the base_dir
    evil_chat_name = "../evil_dir"

    # Now it should be sanitized to '.._evil_dir' or 'evil_dir' depending on basename
    # Actually ../evil_dir with replace / with _ becomes .._evil_dir.
    # Then basename(.._evil_dir) is .._evil_dir.
    # So it should stay within base_dir.

    paths = temp_storage.get_chat_paths(evil_chat_name)

    base_dir_abs = os.path.abspath(temp_storage.base_dir)
    chat_root_abs = os.path.abspath(paths["chat_root"])

    # Ensure it STARTS with base_dir_abs
    assert chat_root_abs.startswith(os.path.join(base_dir_abs, ""))
    assert "evil_dir" in chat_root_abs
    assert os.path.exists(chat_root_abs)

    # Verify it doesn't actually go up
    assert os.path.basename(chat_root_abs) == ".._evil_dir"
