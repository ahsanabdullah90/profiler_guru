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

def test_path_traversal_protection(tmp_path):
    base_dir = tmp_path / "chats"
    sm = StorageManager(base_dir=str(base_dir))

    # Attempt a path traversal attack
    malicious_name = "../malicious"
    paths = sm.get_chat_paths(malicious_name)

    # Verify it was sanitized and stayed within base_dir
    assert os.path.abspath(paths["chat_root"]).startswith(os.path.abspath(os.path.join(str(base_dir), '')))

    # Verify it works even with null bytes
    malicious_name_null = "evil\0path"
    paths_null = sm.get_chat_paths(malicious_name_null)
    assert "\0" not in paths_null["chat_root"]
    assert "evil_path" in paths_null["chat_root"]
