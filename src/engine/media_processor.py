import os
import logging
from pathlib import Path
import faster_whisper

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Handles audio processing and bilingual speech-to-text transcription."""
    def __init__(self):
        self._model = None
        self._initialized = False

    def _init_whisper(self):
        """Lazily and safely initializes the Whisper model, handling dependency or GPU/CPU setup errors."""
        if not self._initialized:
            try:
                # Using the small model balances speed & accuracy for CPU/GPU. Defaulting to cpu.
                self._model = faster_whisper.WhisperModel("small", device="cpu")
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Whisper model: {e}")
                self._model = None
                self._initialized = True  # Set to True so we do not repeatedly throw tracebacks on subsequent calls
        return self._model

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe an audio file to text using faster-whisper.
        Auto-detects language (e.g., Urdu or English).
        Returns a short string or an error message.
        """
        # Convert path to string for os.path check
        path_str = str(audio_path)
        if not os.path.isfile(path_str):
            logger.error(f"Audio not found: {path_str}")
            return "Audio not available."
            
        model = self._init_whisper()
        if model is None:
            logger.error("Whisper model is not initialized. Audio transcription is unavailable.")
            return "Transcription unavailable."

        try:
            # Omitting language parameter enables Whisper's auto-detection of Urdu and English
            segments, info = model.transcribe(path_str)
            logger.info(f"Transcribed audio: detected language '{info.language}' with probability {info.language_probability:.2f}")
            return " ".join([seg.text for seg in segments]).strip()
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return "Transcription failed."

media_processor = MediaProcessor()
