import os
import logging
from pathlib import Path
import faster_whisper

logger = logging.getLogger(__name__)

# Initialise Whisper model lazily
_WHISPER_MODEL = None

def _init_whisper():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        # Using the small model balances speed & accuracy for CPU/GPU
        # Support auto-detection of Urdu & English
        _WHISPER_MODEL = faster_whisper.WhisperModel("small", device="cpu")
    return _WHISPER_MODEL

def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to text using faster‑whisper.
    Auto-detects language (e.g., Urdu or English).
    Returns a short string or an error message.
    """
    if not os.path.isfile(audio_path):
        logger.error(f"Audio not found: {audio_path}")
        return "Audio not available."
    model = _init_whisper()
    try:
        # Omitting language parameter enables Whisper's auto-detection of Urdu and English
        segments, info = model.transcribe(audio_path)
        logger.info(f"Transcribed audio: detected language '{info.language}' with probability {info.language_probability:.2f}")
        return " ".join([seg.text for seg in segments]).strip()
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return "Transcription failed."

class MediaProcessor:
    def transcribe_audio(self, audio_path: str) -> str:
        return transcribe_audio(audio_path)

media_processor = MediaProcessor()
