import pytest
from unittest.mock import MagicMock, patch
import os

from src.engine.media_processor import MediaProcessor
from src.utils.config import config

def test_media_processor_gemini_success(tmp_path, monkeypatch):
    # Setup temporary audio file
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"mock audio content")
    
    # Configure config mock
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "mock_key")
    monkeypatch.setattr(config, "ENABLE_CLOUD_AI", True)
    
    # Create instance
    processor = MediaProcessor()
    
    # Mock GenAI Client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Transcribed speech by Gemini"
    mock_client.models.generate_content.return_value = mock_response
    
    # Inject mock client and prevent loading faster-whisper
    monkeypatch.setattr(processor, "_init_gemini", lambda: mock_client)
    
    # Call transcription
    result = processor.transcribe_audio(str(audio_file))
    
    # Assertions
    assert result == "Transcribed speech by Gemini"
    mock_client.models.generate_content.assert_called_once()

def test_media_processor_gemini_fallback_to_whisper(tmp_path, monkeypatch):
    # Setup temporary audio file
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"mock audio content")
    
    # Configure config mock
    monkeypatch.setattr(config, "GOOGLE_API_KEY", "mock_key")
    monkeypatch.setattr(config, "ENABLE_CLOUD_AI", True)
    
    # Create instance
    processor = MediaProcessor()
    
    # Mock Gemini Client to fail
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("API connection error")
    monkeypatch.setattr(processor, "_init_gemini", lambda: mock_client)
    
    # Mock Whisper model
    mock_whisper = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Transcribed speech by Whisper"
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99
    
    mock_whisper.transcribe.return_value = ([mock_segment], mock_info)
    monkeypatch.setattr(processor, "_init_whisper", lambda: mock_whisper)
    
    # Call transcription
    result = processor.transcribe_audio(str(audio_file))
    
    # Assertions
    assert result == "Transcribed speech by Whisper"
    assert mock_client.models.generate_content.call_count == 4
    mock_whisper.transcribe.assert_called_once()

def test_media_processor_no_gemini_key_uses_whisper(tmp_path, monkeypatch):
    # Setup temporary audio file
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"mock audio content")
    
    # Configure config mock with no key
    monkeypatch.setattr(config, "GOOGLE_API_KEY", None)
    
    # Create instance
    processor = MediaProcessor()
    
    # Mock Whisper model
    mock_whisper = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Transcribed speech by Whisper (No Gemini)"
    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99
    
    mock_whisper.transcribe.return_value = ([mock_segment], mock_info)
    monkeypatch.setattr(processor, "_init_whisper", lambda: mock_whisper)
    
    # Call transcription
    result = processor.transcribe_audio(str(audio_file))
    
    # Assertions
    assert result == "Transcribed speech by Whisper (No Gemini)"
    mock_whisper.transcribe.assert_called_once()
