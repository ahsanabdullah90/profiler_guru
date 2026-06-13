import os
import shutil
import json
import pytest
from src.storage.storage_manager import StorageManager
from src.engine.data_importer import InstagramDataImporter

def test_storage_manager_path_traversal():
    sm = StorageManager("test_chats")

    # Attempting traversal via chat name
    malicious_chat_name = "../external_dir"

    # Should be sanitized to 'external_dir' and kept inside 'test_chats'
    paths = sm.get_chat_paths(malicious_chat_name)

    abs_base = os.path.abspath("test_chats")
    abs_root = os.path.abspath(paths["chat_root"])

    assert abs_root.startswith(abs_base)
    assert os.path.basename(paths["chat_root"]) == "external_dir"

    # Edge case: empty or purely traversal
    assert "unnamed_chat" in sm.get_chat_paths("..")["chat_root"]
    assert "unnamed_chat" in sm.get_chat_paths("/")["chat_root"]

    if os.path.exists("test_chats"):
        shutil.rmtree("test_chats")

def test_importer_path_traversal(tmp_path):
    # Setup mock export
    export_dir = tmp_path / "export"
    inbox_dir = export_dir / "messages" / "inbox" / "chat1"
    inbox_dir.mkdir(parents=True)

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("secret info")

    message_data = {
        "title": "Chat 1",
        "messages": [
            {
                "sender_name": "User",
                "timestamp_ms": 1000,
                "content": "Hello",
                "photos": [{"uri": "../../secret.txt"}]
            }
        ]
    }

    (inbox_dir / "message_1.json").write_text(json.dumps(message_data))

    chats_dir = tmp_path / "chats"
    sm = StorageManager(str(chats_dir))
    importer = InstagramDataImporter(sm)

    # Mock media processor to avoid external calls/errors
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("src.engine.data_importer.describe_image", lambda x: "desc")
        mp.setattr("src.engine.data_importer.rag_engine.add_messages_to_index", lambda *args: None)

        importer.import_from_json(str(export_dir))

    # Check that secret.txt was NOT copied
    copied_secret = chats_dir / "Chat 1" / "Media" / "secret.txt"
    assert not copied_secret.exists()
