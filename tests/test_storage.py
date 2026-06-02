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

def test_path_traversal_protection(temp_storage):
    """
    Test that path traversal attempts are neutralized.
    """
    traversal_name = "../malicious_dir"
    paths = temp_storage.get_chat_paths(traversal_name)

    # The chat_root should be inside temp_storage.base_dir
    base_dir_abs = os.path.abspath(temp_storage.base_dir)
    chat_root_abs = os.path.abspath(paths["chat_root"])

    assert chat_root_abs.startswith(base_dir_abs)
    assert ".." not in paths["chat_root"]
    assert "malicious_dir" in paths["chat_root"]
