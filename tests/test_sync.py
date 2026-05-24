import pytest
import os
from unittest.mock import MagicMock, patch
from src.engine.instagram_sync import InstagramSync
from datetime import datetime

@pytest.fixture
def mock_sync(temp_storage):
    with patch('src.engine.instagram_sync.Client') as mock_client:
        sync = InstagramSync()
        sync.cl = mock_client()
        sync.sm = temp_storage
        return sync

def test_sync_fetch_messages(mock_sync, temp_rag_engine):
    # Setup mock threads and messages
    mock_thread = MagicMock()
    mock_thread.thread_title = "Alice"
    mock_thread.id = "123"
    mock_sync.cl.direct_threads.return_value = [mock_thread]

    mock_message = MagicMock()
    mock_message.text = "Hey!"
    mock_message.timestamp = datetime(2023, 11, 14, 10, 0, 0)
    mock_message.user_id = "user_alice"
    mock_message.clip = None
    mock_sync.cl.direct_messages.return_value = [mock_message]

    with patch('src.engine.instagram_sync.rag_engine', temp_rag_engine):
        mock_sync.fetch_new_messages()

    # Verify message was saved
    chat_paths = mock_sync.sm.get_chat_paths("Alice")
    files = os.listdir(chat_paths["chats_dir"])
    assert len(files) > 0
    with open(os.path.join(chat_paths["chats_dir"], files[0]), "r") as f:
        content = f.read()
        assert "Hey!" in content
