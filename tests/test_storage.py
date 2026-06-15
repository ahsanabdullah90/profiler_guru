import os
from datetime import datetime
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

def test_save_message_with_datetime(temp_storage):
    chat_name = "test_user_dt"
    sender = "Bob"
    text = "Hello with datetime!"
    dt = datetime(2024, 1, 15, 10, 30, 0)

    content, file_path, quarter_id = temp_storage.save_message(chat_name, sender, text, dt)

    assert os.path.exists(file_path)
    assert "2024_Q1" in file_path
    assert "[2024-01-15 10:30:00]" in content
    assert "Bob" in content
    assert "Hello with datetime!" in content

def test_save_message_with_float_timestamp(temp_storage):
    chat_name = "test_user_float"
    sender = "Charlie"
    text = "Hello with float!"
    timestamp = 1704067200000.0 # 2024-01-01 00:00:00

    content, file_path, quarter_id = temp_storage.save_message(chat_name, sender, text, timestamp)

    assert os.path.exists(file_path)
    assert "2024_Q1" in file_path
    assert "[2024-01-01 00:00:00]" in content
    assert "Charlie" in content
    assert "Hello with float!" in content
