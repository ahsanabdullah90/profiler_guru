import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.engine.data_importer import InstagramDataImporter

def test_import_file_read_error(tmp_path, temp_storage):
    # Setup mock Instagram export structure with TWO files
    export_path = tmp_path / "instagram_export"
    messages_path = export_path / "messages" / "inbox" / "alice_123"
    messages_path.mkdir(parents=True)

    # File 1: Valid
    msg1_data = {
        "title": "Alice",
        "messages": [{"sender_name": "Alice", "timestamp_ms": 1700000000000, "content": "Valid message"}]
    }
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump(msg1_data, f)

    # File 2: Also valid on disk, but we will mock open to fail for it
    msg2_data = {
        "title": "Alice",
        "messages": [{"sender_name": "Alice", "timestamp_ms": 1700000060000, "content": "This will fail"}]
    }
    file2_path = messages_path / "message_2.json"
    with open(file2_path, "w", encoding='utf-8') as f:
        json.dump(msg2_data, f)

    importer = InstagramDataImporter(temp_storage)

    # Mock rag_engine to avoid DB side effects
    with patch('src.engine.data_importer.rag_engine') as mock_rag:
        # Mock open to raise OSError only for message_2.json
        original_open = open
        def side_effect(file, *args, **kwargs):
            if str(file).endswith("message_2.json"):
                raise OSError("Simulated read error")
            return original_open(file, *args, **kwargs)

        with patch('builtins.open', side_effect=side_effect):
            success = importer.import_from_json(str(export_path))

    assert success is True
    # Verify that the valid message was processed (we can check if rag_engine.add_messages_to_index was called)
    # message_1.json should have been processed.
    assert mock_rag.add_messages_to_index.called

def test_import_invalid_json(tmp_path, temp_storage):
    # Setup mock Instagram export structure
    export_path = tmp_path / "instagram_export"
    messages_path = export_path / "messages" / "inbox" / "bob_456"
    messages_path.mkdir(parents=True)

    # File 1: Malformed JSON
    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        f.write("{ invalid json: ")

    # File 2: Valid JSON
    msg2_data = {
        "title": "Bob",
        "messages": [{"sender_name": "Bob", "timestamp_ms": 1700000060000, "content": "I am valid"}]
    }
    with open(messages_path / "message_2.json", "w", encoding='utf-8') as f:
        json.dump(msg2_data, f)

    importer = InstagramDataImporter(temp_storage)

    with patch('src.engine.data_importer.rag_engine') as mock_rag:
        success = importer.import_from_json(str(export_path))

    assert success is True
    # Verify that message_2.json was processed
    any_valid = False
    for call in mock_rag.add_messages_to_index.call_args_list:
        if "I am valid" in str(call):
            any_valid = True
    assert any_valid
