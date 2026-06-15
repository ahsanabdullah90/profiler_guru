import os
import pytest
from unittest.mock import MagicMock, patch
from src.engine.media_processor import describe_image, transcribe_audio, media_processor

def test_describe_image_not_found():
    result = describe_image("/non/existent/image.jpg")
    assert result == "Image not available."

def test_describe_image_fallback_no_gemini(tmp_path):
    img_path = tmp_path / "sunny_beach.jpg"
    img_path.write_text("dummy content")

    with patch("src.engine.media_processor._GEMINI_MODEL", None):
        result = describe_image(str(img_path))
        assert result == "Sunny Beach"

def test_describe_image_happy_path(tmp_path):
    img_path = tmp_path / "test_image.png"
    img_path.write_text("dummy data")

    mock_gemini = MagicMock()
    mock_response = MagicMock()
    mock_response.text = " A beautiful landscape. "
    mock_gemini.generate_content.return_value = mock_response

    with patch("src.engine.media_processor._GEMINI_MODEL", mock_gemini):
        result = describe_image(str(img_path))
        assert result == "A beautiful landscape."
        mock_gemini.generate_content.assert_called_once()

def test_describe_image_gemini_failure_fallback(tmp_path):
    img_path = tmp_path / "mountain_view.jpg"
    img_path.write_text("dummy")

    mock_gemini = MagicMock()
    mock_gemini.generate_content.side_effect = Exception("Gemini error")

    with patch("src.engine.media_processor._GEMINI_MODEL", mock_gemini):
        result = describe_image(str(img_path))
        assert result == "Mountain View"

def test_transcribe_audio_not_found():
    result = transcribe_audio("/non/existent/audio.mp3")
    assert result == "Audio not available."

def test_transcribe_audio_happy_path(tmp_path):
    audio_path = tmp_path / "speech.mp3"
    audio_path.write_text("dummy audio")

    mock_whisper = MagicMock()
    mock_segment = MagicMock()
    mock_segment.text = "Hello world"
    mock_whisper.transcribe.return_value = ([mock_segment], None)

    with patch("src.engine.media_processor._init_whisper", return_value=mock_whisper):
        result = transcribe_audio(str(audio_path))
        assert result == "Hello world"

def test_transcribe_audio_failure(tmp_path):
    audio_path = tmp_path / "corrupt.mp3"
    audio_path.write_text("bad data")

    mock_whisper = MagicMock()
    mock_whisper.transcribe.side_effect = Exception("Whisper error")

    with patch("src.engine.media_processor._init_whisper", return_value=mock_whisper):
        result = transcribe_audio(str(audio_path))
        assert result == "Transcription failed."

def test_media_processor_shim(tmp_path):
    # Verify the shim works as expected
    img_path = tmp_path / "shim_test.jpg"
    img_path.write_text("data")

    with patch("src.engine.media_processor._GEMINI_MODEL", None):
        assert media_processor.describe_image(str(img_path)) == "Shim Test"

    assert media_processor.transcribe_audio("/no/audio") == "Audio not available."
