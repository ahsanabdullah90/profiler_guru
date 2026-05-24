import os
import torch
import whisper
from faster_whisper import WhisperModel
from PIL import Image
import google.generativeai as genai
import requests
import json
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

        self.ollama_url = "http://localhost:11434/api/generate"

    def setup_whisper(self):
        try:
            if self.device == "cuda":
                logger.info("Loading standard Whisper model: base on cuda")
                self.whisper_model = whisper.load_model("base", device="cuda")
                self.is_faster = False
            else:
                logger.info("Loading faster-whisper model: small on cpu")
                # compute_type="int8" is good for CPU
                self.whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
                self.is_faster = True
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")

    def transcribe_audio(self, audio_path):
        if not self.whisper_model:
            return "Transcription unavailable (model not loaded)"
        try:
            if self.is_faster:
                segments, info = self.whisper_model.transcribe(audio_path, beam_size=5)
                return " ".join([segment.text for segment in segments])
            else:
                result = self.whisper_model.transcribe(audio_path)
                return result.get("text", "")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return f"Error transcribing audio: {e}"

    def describe_image(self, image_path):
        # Try Ollama first if GPU is enabled
        if self.device == "cuda":
            desc = self._describe_with_ollama(image_path)
            if desc:
                return desc

        # Fallback to Gemini
        if self.gemini_model:
            try:
                img = Image.open(image_path)
                prompt = "Describe this image in detail for an Instagram DM conversation context."
                response = self.gemini_model.generate_content([prompt, img])
                return response.text
            except Exception as e:
                logger.error(f"Gemini image description error: {e}")
                return f"Error describing image with Gemini: {e}"

        return "Image description unavailable."

    def _describe_with_ollama(self, image_path):
        import base64
        try:
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')

            payload = {
                "model": "llava", # common vision model for ollama
                "prompt": "Describe this image for an Instagram DM context.",
                "stream": False,
                "images": [img_data]
            }

            response = requests.post(self.ollama_url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            logger.debug(f"Ollama description failed (maybe not running): {e}")
        return None

media_processor = MediaProcessor()
