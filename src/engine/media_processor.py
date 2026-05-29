import os
import logging
from pathlib import Path

import google.generativeai as genai
import faster_whisper

logger = logging.getLogger(__name__)

# Initialise Gemini model once (optional)
def _init_gemini():
    from src.utils.config import config
    if config.GOOGLE_API_KEY:
        genai.configure(api_key=config.GOOGLE_API_KEY)
        return genai.GenerativeModel('gemini-1.5-flash')
    return None

_GEMINI_MODEL = _init_gemini()

# Initialise Whisper model lazily
_WHISPER_MODEL = None

def _init_whisper():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        # Using the small model balances speed & accuracy for CPU/GPU
        _WHISPER_MODEL = faster_whisper.WhisperModel("small", device="cpu")
    return _WHISPER_MODEL

def describe_image(image_path: str) -> str:
    """Return a short description of an image.
    Uses Gemini if available; falls back to filename‑based description.
    """
    if not os.path.isfile(image_path):
        logger.error(f"Image not found: {image_path}")
        return "Image not available."

    if _GEMINI_MODEL:
        try:
            with open(image_path, "rb") as img:
                response = _GEMINI_MODEL.generate_content([
                    "Describe this image in one concise sentence.",
                    img.read()
                ])
            return response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini image description failed: {e}")
    # Simple fallback – use filename as description
    return Path(image_path).stem.replace("_", " ").title()

def transcribe_audio(audio_path: str) -> str:
    """Transcribe an audio file to text using faster‑whisper.
    Returns a short string or an error message.
    """
    if not os.path.isfile(audio_path):
        logger.error(f"Audio not found: {audio_path}")
        return "Audio not available."
    model = _init_whisper()
    try:
        segments, _ = model.transcribe(audio_path, language="en")
        return " ".join([seg.text for seg in segments]).strip()
    except Exception as e:
        logger.error(f"Audio transcription failed: {e}")
        return "Transcription failed."

class MediaProcessor:
    def describe_image(self, image_path: str) -> str:
        return describe_image(image_path)
    def transcribe_audio(self, audio_path: str) -> str:
        return transcribe_audio(audio_path)

media_processor = MediaProcessor()
