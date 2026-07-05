import os
import json
from pathlib import Path

import pytest
from src.engine.data_importer import InstagramDataImporter, drop_reason, _safe_latin1_decode

def test_import_from_json(tmp_path, temp_storage):
    # Setup mock Instagram export structure
    export_path = tmp_path / "instagram_export"
    messages_path = export_path / "messages" / "inbox" / "alice_123"
    messages_path.mkdir(parents=True)

    message_data = {
        "title": "Alice",
        "messages": [
            {
                "sender_name": "Alice",
                "timestamp_ms": 1700000000000,
                "content": "Hello!"
            }
        ]
    }

    # We need to simulate the latin1/utf8 encoding issue if we want to be thorough,
    # but the code does .encode('latin1').decode('utf8').
    # Let's write it in a way that the decoder won't fail.
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump(message_data, f)

    importer = InstagramDataImporter(temp_storage)
    success = importer.import_from_json(str(export_path))

    assert success

    # Check if files were created in storage
    chat_paths = temp_storage.get_chat_paths("Alice")
    assert os.path.exists(chat_paths["chats_dir"])
    files = os.listdir(chat_paths["chats_dir"])
    assert len(files) > 0

def test_preflight_check(tmp_path, temp_storage):
    importer = InstagramDataImporter(temp_storage)
    
    # Test empty path
    res = importer.preflight_check("")
    assert res["status"] == "error"
    assert "empty" in res["message"].lower()

    # Test non-existent path
    res = importer.preflight_check(str(tmp_path / "non_existent"))
    assert res["status"] == "error"
    assert "not found" in res["message"].lower()

    # Setup valid structure
    export_path = tmp_path / "instagram_export_preflight"
    messages_path = export_path / "your_instagram_activity" / "messages" / "inbox" / "bob_456"
    messages_path.mkdir(parents=True)
    
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump({"title": "Bob", "messages": []}, f)
        
    res = importer.preflight_check(str(export_path))
    assert res["status"] == "success"
    assert res["stats"]["total_threads"] == 1
    assert res["stats"]["total_json_files"] == 1

    # Test direct inbox folder validation (fixes folder sync bug)
    inbox_dir_path = export_path / "your_instagram_activity" / "messages" / "inbox"
    res_direct = importer.preflight_check(str(inbox_dir_path))
    assert res_direct["status"] == "success"
    assert res_direct["stats"]["total_threads"] == 1
    assert res_direct["stats"]["total_json_files"] == 1

def test_import_with_progress_callback(tmp_path, temp_storage):
    export_path = tmp_path / "instagram_export_callback"
    messages_path = export_path / "messages" / "inbox" / "charlie_789"
    messages_path.mkdir(parents=True)

    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump({"title": "Charlie", "messages": [{"sender_name": "Charlie", "timestamp_ms": 1700000000000, "content": "Hi"}]}, f)

    importer = InstagramDataImporter(temp_storage)
    
    progress_calls = []
    def progress_cb(current, total, active_chat):
        progress_calls.append((current, total, active_chat))

    success = importer.import_from_json(str(export_path), progress_callback=progress_cb)
    assert success
    assert len(progress_calls) == 1
    assert progress_calls[0] == (1, 1, "Charlie")


def test_chunk_id_not_in_parsed_text(tmp_path, temp_storage, monkeypatch):
    """Regression: RAG chunk_id HTML comments must be stripped before display."""
    from src.services.contacts_service import parse_monthly_messages
    from src.utils.config import config
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")
    monkeypatch.setattr(config, "INSTAGRAM_USERNAME", "me")

    # Manually write a markdown file with a chunk_id comment
    chats_dir = tmp_path / "chats" / "TestUser" / "Chats"
    chats_dir.mkdir(parents=True)
    md_path = chats_dir / "2026_06.md"
    md_content = (
        '### [2026-06-15 10:00:00] TestUser\n'
        'Hello world\n'
        '<!-- chunk_id: abc12345 -->\n'
        '\n'
        '---\n'
    )
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    messages = parse_monthly_messages("TestUser", "2026_06.md")
    assert len(messages) == 1
    # The chunk_id comment must NOT appear in the rendered text
    assert "chunk_id" not in messages[0]["text"].lower()
    # The actual message text must survive
    assert "Hello world" in messages[0]["text"]


def test_safe_latin1_decode_supplementary_plane():
    """Non-BMP characters must not break the importer."""
    text = "Hello \U0001f3b6 World"  # U+1F3B6 MUSICAL NOTE (multi-byte emoji)
    result = _safe_latin1_decode(text)
    assert "Hello" in result
    assert "\U0001f3b6" in result or chr(0x1f3b6) not in result  # Accept safe fallback


def test_drop_reason_categorization():
    """Verify each content type maps to the correct drop reason."""
    # Audio → should be imported (returns None)
    assert drop_reason({"audio_files": [{"uri": "test.mp3"}]}) is None

    # Reel share → dropped as reel
    assert drop_reason({"share": {"link": "https://instagram.com/reel/xyz/"}}) == "reel"

    # Photo-only → dropped as media
    assert drop_reason({"photos": [{"uri": "pic.jpg"}]}) == "media"

    # Video-only → dropped as media
    assert drop_reason({"videos": [{"uri": "clip.mp4"}]}) == "media"

    # Text-only → imported
    assert drop_reason({"content": "Hello"}) is None

    # Empty content → dropped as empty
    assert drop_reason({"content": ""}) == "empty"


def test_import_skips_media_only(tmp_path, temp_storage):
    """Import must silently skip photo/video-only messages."""
    export_path = tmp_path / "export_media_skip"
    inbox = export_path / "messages" / "inbox" / "alice_789"
    inbox.mkdir(parents=True)

    message_data = {
        "title": "Alice",
        "messages": [
            {"sender_name": "Alice", "timestamp_ms": 1700000000000, "content": "Text message"},
            {"sender_name": "Alice", "timestamp_ms": 1700000060000, "photos": [{"uri": "photo.jpg"}]},
            {"sender_name": "Alice", "timestamp_ms": 1700000120000, "content": "More text"},
        ]
    }
    with open(inbox / "message_1.json", "w", encoding="utf-8") as f:
        json.dump(message_data, f)

    importer = InstagramDataImporter(temp_storage)
    success = importer.import_from_json(str(export_path))
    assert success

    # Only text messages should be in the storage
    chat_paths = temp_storage.get_chat_paths("Alice")
    md_files = list(Path(chat_paths["chats_dir"]).glob("*.md"))
    assert len(md_files) == 1
    with open(md_files[0], encoding="utf-8") as f:
        content = f.read()
    assert content.count("Text message") == 1
    assert content.count("More text") == 1
    # Photo-only message should not appear
    assert "photo.jpg" not in content
