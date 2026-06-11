import os
import json
import tempfile
import pytest
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter
from unittest.mock import MagicMock
from src.engine import media_processor

def test_path_traversal_storage_manager():
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = StorageManager(base_dir=tmpdir)
        # Attempt to create a directory outside base_dir
        evil_chat_name = "../evil_dir"
        paths = sm.get_chat_paths(evil_chat_name)

        expected_evil_dir = os.path.abspath(os.path.join(tmpdir, "..", "evil_dir"))
        # After fix, it should NOT exist
        assert not os.path.exists(expected_evil_dir)

        # It should have been sanitized to something inside tmpdir
        assert os.path.abspath(paths["chat_root"]).startswith(os.path.abspath(tmpdir))

def test_path_traversal_importer():
    with tempfile.TemporaryDirectory() as export_dir:
        with tempfile.TemporaryDirectory() as storage_dir:
            # Create a fake export
            inbox_root = os.path.join(export_dir, 'messages', 'inbox')
            chat_folder = 'attacker_chat_123'
            full_chat_path = os.path.join(inbox_root, chat_folder)
            os.makedirs(full_chat_path)

            # Create a sensitive file OUTSIDE export_dir
            parent_dir = os.path.dirname(export_dir)
            sensitive_file = os.path.join(parent_dir, "sensitive_outside.txt")
            with open(sensitive_file, "w") as f:
                f.write("secret data outside")

            # Create malicious JSON
            message_data = {
                "title": "attacker_chat",
                "messages": [
                    {
                        "sender_name": "Attacker",
                        "timestamp_ms": 1700000000000,
                        "content": "Stealing your data",
                        "photos": [
                            {
                                "uri": "../sensitive_outside.txt"
                            }
                        ]
                    }
                ]
            }
            with open(os.path.join(full_chat_path, "message_1.json"), "w") as f:
                json.dump(message_data, f)

            sm = StorageManager(base_dir=storage_dir)
            importer = InstagramDataImporter(sm)

            # Mock media_processor to avoid external calls
            media_processor.describe_image = MagicMock(return_value="mock description")

            importer.import_from_json(export_dir)

            # Check if sensitive_outside.txt was NOT copied into storage
            stolen_file_path = os.path.join(storage_dir, "attacker_chat", "Media", "sensitive_outside.txt")
            assert not os.path.exists(stolen_file_path)

def test_path_traversal_importer_prefix_bypass():
    with tempfile.TemporaryDirectory() as tmp_root:
        export_dir = os.path.join(tmp_root, "data")
        os.makedirs(export_dir)

        secret_dir = os.path.join(tmp_root, "data_secrets")
        os.makedirs(secret_dir)

        secret_file = os.path.join(secret_dir, "secret.txt")
        with open(secret_file, "w") as f:
            f.write("top secret")

        with tempfile.TemporaryDirectory() as storage_dir:
            inbox_root = os.path.join(export_dir, 'messages', 'inbox')
            os.makedirs(inbox_root)

            message_data = {
                "title": "attacker",
                "messages": [{
                    "sender_name": "Attacker",
                    "timestamp_ms": 1700000000000,
                    "content": "Stealing",
                    "photos": [{"uri": "../data_secrets/secret.txt"}]
                }]
            }
            chat_path = os.path.join(inbox_root, "attacker")
            os.makedirs(chat_path)
            with open(os.path.join(chat_path, "message_1.json"), "w") as f:
                json.dump(message_data, f)

            sm = StorageManager(base_dir=storage_dir)
            importer = InstagramDataImporter(sm)
            media_processor.describe_image = MagicMock(return_value="mock")

            importer.import_from_json(export_dir)

            stolen_file_path = os.path.join(storage_dir, "attacker", "Media", "secret.txt")
            assert not os.path.exists(stolen_file_path)
