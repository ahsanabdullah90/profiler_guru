import os
import pytest
from src.utils.config import Config

def test_validate_warning_when_api_key_missing(monkeypatch, capsys, tmp_path):
    # Set GOOGLE_API_KEY to None
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", None)

    # Use a temporary directory for CHATS_DIR to avoid side effects
    test_chats_dir = tmp_path / "chats_dir_warning"
    monkeypatch.setattr(Config, "CHATS_DIR", str(test_chats_dir))

    Config.validate()

    captured = capsys.readouterr()
    assert "Warning: GOOGLE_API_KEY not found in environment." in captured.out
    assert os.path.exists(test_chats_dir)

def test_validate_creates_chats_dir_if_not_exists(monkeypatch, tmp_path):
    # Set GOOGLE_API_KEY to something so it doesn't print warning (optional)
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "fake_key")

    # Set CHATS_DIR to a non-existent path in tmp_path
    test_chats_dir = tmp_path / "non_existent_chats"
    monkeypatch.setattr(Config, "CHATS_DIR", str(test_chats_dir))

    assert not os.path.exists(test_chats_dir)

    Config.validate()

    assert os.path.exists(test_chats_dir)
    assert os.path.isdir(test_chats_dir)

def test_validate_no_warning_when_api_key_present(monkeypatch, capsys, tmp_path):
    # Set GOOGLE_API_KEY to a value
    monkeypatch.setattr(Config, "GOOGLE_API_KEY", "valid_key")

    # Use a temporary directory for CHATS_DIR
    test_chats_dir = tmp_path / "chats_dir_present"
    monkeypatch.setattr(Config, "CHATS_DIR", str(test_chats_dir))

    Config.validate()

    captured = capsys.readouterr()
    assert "Warning: GOOGLE_API_KEY not found in environment." not in captured.out
    assert os.path.exists(test_chats_dir)
