import os
import logging
from pathlib import Path

import google.generativeai as genai
import faster_whisper

logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self):
        self._gemini_model = None
        self._whisper_model = None
        self._initialized_gemini = False

    def _get_gemini(self):
        if not self._initialized_gemini:
            from src.utils.config import config
            if config.GOOGLE_API_KEY:
                try:
                    genai.configure(api_key=config.GOOGLE_API_KEY)
                    self._gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini: {e}")
            self._initialized_gemini = True
        return self._gemini_model

    def _get_whisper(self):
        if self._whisper_model is None:
            from src.utils.config import config
            try:
                # Using the small model balances speed & accuracy for CPU/GPU
                self._whisper_model = faster_whisper.WhisperModel("small", device=config.DEVICE)
            except Exception as e:
                logger.error(f"Failed to initialize Whisper: {e}")
        return self._whisper_model

    def describe_image(self, image_path: str) -> str:
        """Return a short description of an image.
        Uses Gemini if available; falls back to filename‑based description.
        """
        if not os.path.isfile(image_path):
            logger.error(f"Image not found: {image_path}")
            return "Image not available."

        model = self._get_gemini()
        if model:
            try:
                with open(image_path, "rb") as img:
                    response = model.generate_content([
                        "Describe this image in one concise sentence.",
                        img.read()
                    ])
                return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini image description failed: {e}")
        # Simple fallback – use filename as description
        return Path(image_path).stem.replace("_", " ").title()

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe an audio file to text using faster‑whisper.
        Returns a short string or an error message.
        """
        if not os.path.isfile(audio_path):
            logger.error(f"Audio not found: {audio_path}")
            return "Audio not available."

        model = self._get_whisper()
        if not model:
            return "Transcription failed: Whisper model not initialized."

        try:
            segments, _ = model.transcribe(audio_path, language="en")
            return " ".join([seg.text for seg in segments]).strip()
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return "Transcription failed."

media_processor = MediaProcessor()

# Backward compatibility exports
def describe_image(image_path: str) -> str:
    return media_processor.describe_image(image_path)

def transcribe_audio(audio_path: str) -> str:
    return media_processor.transcribe_audio(audio_path)
