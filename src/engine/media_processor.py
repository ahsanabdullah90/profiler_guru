import os
import logging
from pathlib import Path

import google.generativeai as genai
import faster_whisper

logger = logging.getLogger(__name__)

class MediaProcessor:
    def __init__(self):
        # Initialise Gemini model once (optional)
        self._gemini_model = self._init_gemini()
        # Initialise Whisper model lazily
        self._whisper_model = None

    def _init_gemini(self):
        try:
            from src.utils.config import config
            if config.GOOGLE_API_KEY:
                genai.configure(api_key=config.GOOGLE_API_KEY)
                return genai.GenerativeModel('gemini-1.5-flash')
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini: {e}")
        return None

    def _init_whisper(self):
        if self._whisper_model is None:
            try:
                from src.utils.config import config
                # Using the small model balances speed & accuracy for CPU/GPU
                self._whisper_model = faster_whisper.WhisperModel("small", device=config.DEVICE)
            except Exception as e:
                logger.error(f"Failed to initialize Whisper: {e}")
                raise
        return self._whisper_model

    def describe_image(self, image_path: str) -> str:
        """Return a short description of an image.
        Uses Gemini if available; falls back to filename‑based description.
        """
        if not os.path.isfile(image_path):
            logger.error(f"Image not found: {image_path}")
            return "Image not available."

        if self._gemini_model:
            try:
                with open(image_path, "rb") as img:
                    response = self._gemini_model.generate_content([
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
        try:
            model = self._init_whisper()
            segments, _ = model.transcribe(audio_path, language="en")
            return " ".join([seg.text for seg in segments]).strip()
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return "Transcription failed."

media_processor = MediaProcessor()
