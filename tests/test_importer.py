import os
import json
import pytest
from src.engine.data_importer import InstagramDataImporter

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
