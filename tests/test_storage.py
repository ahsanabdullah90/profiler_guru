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
    assert os.path.exists(paths["audio_dir"])
    # Verify structure: chat_root contains Chats/ and Audio/
    assert os.path.basename(paths["chats_dir"]) == "Chats"
    assert os.path.basename(paths["audio_dir"]) == "Audio"
    # Verify paths contain the sanitized contact name
    assert "test_user" in paths["chat_root"]


def test_save_message(temp_storage):
    chat_name = "test_user"
    sender = "Alice"
    text = "Hello!"
    timestamp = 1700000000000  # 2023-11-14

    content, file_path, month_id = temp_storage.save_message(chat_name, sender, text, timestamp)

    assert os.path.exists(file_path)
    assert "2023_11" in file_path
    assert month_id == "2023_11"

    # Verify markdown structure: header + body + chunk_id + separator
    assert content.startswith("### [")
    assert sender in content
    assert text in content
    assert "<!-- chunk_id:" in content
    assert "---" in content

    with open(file_path, "r", encoding="utf-8") as f:
        saved_content = f.read()
        assert "Alice" in saved_content
        assert "Hello!" in saved_content
        assert "<!-- chunk_id:" in saved_content


def test_save_message_audio(temp_storage):
    """Audio messages should include an [Audio] markdown link."""
    content, file_path, _ = temp_storage.save_message(
        "Bob", "Bob", "Voice note", 1700000000000,
        media_type="audio", media_local_path="/fake/audio.mp3"
    )
    assert "[Audio](" in content
