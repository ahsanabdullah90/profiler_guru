import os
import torch
import whisper
from PIL import Image
import google.generativeai as genai
from src.utils.config import config
from src.utils.logger import logger

class MediaProcessor:
    def __init__(self):
        self.device = config.DEVICE
        self.whisper_model = None
        self.setup_whisper()

        # Google AI Setup
        if config.GOOGLE_API_KEY:
            genai.configure(api_key=config.GOOGLE_API_KEY)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.gemini_model = None

    def setup_whisper(self):
        try:
            model_size = "base" if self.device == "cuda" else "small"
            logger.info(f"Loading Whisper model: {model_size} on {self.device}")
            self.whisper_model = whisper.load_model(model_size, device=self.device)
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")

    def transcribe_audio(self, audio_path):
        if not self.whisper_model:
            return "Transcription unavailable (model not loaded)"
        try:
            result = self.whisper_model.transcribe(audio_path)
            return result.get("text", "")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error transcribing audio: {e}"

    def describe_image(self, image_path):
        # Prefer local Ollama if GPU is available (placeholder logic as requested)
        # For now, implementing Gemini as the primary multimodal engine
        if not self.gemini_model:
            return "Image description unavailable (No API key or model)"

        try:
            img = Image.open(image_path)
            prompt = "Describe this image in detail, focusing on what might be relevant for an Instagram DM conversation context."
            response = self.gemini_model.generate_content([prompt, img])
            return response.text
        except Exception as e:
            logger.error(f"Image description error: {e}")
            return f"Error describing image: {e}"

media_processor = MediaProcessor()
