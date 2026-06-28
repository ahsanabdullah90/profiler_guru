import pytest
import os
from unittest.mock import MagicMock, patch
from src.engine.instagram_sync import InstagramSync
from datetime import datetime

@pytest.fixture
def mock_sync(temp_storage):
    with patch('src.engine.instagram_sync.Client') as mock_client, \
         patch('src.engine.instagram_sync.InstagramSync._save_to_keyring') as mock_save_keyring:
        mock_inst = mock_client()
        mock_client.return_value = mock_inst
        sync = InstagramSync()
        sync.cl = mock_inst
        sync.sm = temp_storage
        yield sync


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

def test_login_success_with_saved_session(mock_sync):
    with patch('os.path.exists', return_value=True):
        mock_sync.cl.get_timeline_feed.return_value = True
        
        status, info = mock_sync.login("user", "pass")
        
        assert status == "success"
        mock_sync.cl.load_settings.assert_called_once_with(mock_sync.session_path)
        mock_sync.cl.get_timeline_feed.assert_called_once()

def test_login_expired_session_fresh_success(mock_sync):
    with patch('os.path.exists', return_value=True), \
         patch('os.remove') as mock_remove:
        mock_sync.cl.get_timeline_feed.side_effect = Exception("Expired")
        
        status, info = mock_sync.login("user", "pass")
        
        assert status == "success"
        mock_sync.cl.load_settings.assert_called_once_with(mock_sync.session_path)
        mock_remove.assert_called_once_with(mock_sync.session_path)
        mock_sync.cl.login.assert_called_once_with("user", "pass")

def test_login_standard_2fa_required(mock_sync):
    with patch('os.path.exists', return_value=False):
        mock_sync.cl.login.side_effect = Exception("two-factor authentication required")
        
        status, info = mock_sync.login("user", "pass")
        
        assert status == "2fa_required"
        assert "two-factor" in info

def test_login_with_2fa_code_two_step_success(mock_sync):
    # If 2FA code is provided, we should not attempt load_settings, and try two_factor_login
    with patch('os.path.exists', return_value=True) as mock_exists:
        status, info = mock_sync.login("user", "pass", verification_code="123456")
        
        assert status == "success"
        # Ensure os.path.exists was not called with the session path
        session_path_called = any(
            mock_sync.session_path in args or str(mock_sync.session_path) in args
            for args, _ in mock_exists.call_args_list
        )
        assert not session_path_called, f"os.path.exists should not be called with session path {mock_sync.session_path}"
        mock_sync.cl.two_factor_login.assert_called_once_with("123456")
        mock_sync.cl.dump_settings.assert_called_once_with(mock_sync.session_path)

def test_login_with_2fa_code_fallback_success(mock_sync):
    # If two_factor_login fails, we should fall back to direct login(verification_code=...)
    with patch('os.path.exists', return_value=False):
        mock_sync.cl.two_factor_login.side_effect = Exception("Method not allowed or direct required")
        
        status, info = mock_sync.login("user", "pass", verification_code="123456")
        
        assert status == "success"
        mock_sync.cl.two_factor_login.assert_called_once_with("123456")
        # In the fallback, the client is re-created, so we check if login was called on the mock client
        # since it's a mock Client, any new instances will share mock behaviors or we can check the calls.
        # Let's verify that the fallback login call was attempted.
        assert mock_sync.cl.login.call_count == 1
        # The fallback login call should pass verification_code
        mock_sync.cl.login.assert_called_with("user", "pass", verification_code="123456")

def test_sync_active_syncs_tracking(mock_sync, temp_rag_engine):
    mock_thread = MagicMock()
    mock_thread.thread_title = "Alice"
    mock_thread.id = "123"
    
    mock_message = MagicMock()
    mock_message.text = "Hey!"
    mock_message.timestamp = datetime(2023, 11, 14, 10, 0, 0)
    mock_message.user_id = "user_alice"
    mock_message.clip = None
    mock_sync.cl.direct_messages.return_value = [mock_message]
    
    # Assert that Alice is in active_syncs during save_message call
    original_save = mock_sync.sm.save_message
    
    def mock_save(*args, **kwargs):
        assert "Alice" in mock_sync.active_syncs
        return original_save(*args, **kwargs)
        
    mock_sync.sm.save_message = mock_save
    
    with patch('src.engine.instagram_sync.rag_engine', temp_rag_engine):
        mock_sync.sync_thread_messages(mock_thread)
        
    # Assert that after sync is complete, it has been removed from active_syncs
    assert "Alice" not in mock_sync.active_syncs

