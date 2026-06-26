import logging
import os

import faster_whisper

logger = logging.getLogger(__name__)

class MediaProcessor:
    """Handles audio processing and bilingual speech-to-text transcription."""
    def __init__(self):
        self._model = None
        self._initialized = False
        self._gemini_client = None
        self._gemini_initialized = False

    def _init_gemini(self):
        """Lazily and safely initializes the Gemini client, handling key or import errors."""
        if not self._gemini_initialized:
            from src.utils.config import config
            if config.GOOGLE_API_KEY and config.ENABLE_CLOUD_AI:
                try:
                    from google import genai
                    logger.info("Initializing Gemini Client for audio transcription...")
                    self._gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
                except Exception as e:
                    logger.error(f"Failed to initialize Gemini Client for transcription: {e}")
            self._gemini_initialized = True
        return self._gemini_client

    def _init_whisper(self):
        """Lazily and safely initializes the Whisper model, handling dependency or GPU/CPU setup errors."""
        if not self._initialized:
            from src.utils.config import config
            device = config.DEVICE
            compute_type = "float16" if device == "cuda" else "int8"
            
            try:
                logger.info(f"Initializing Whisper model on device: {device} (compute_type: {compute_type})...")
                self._model = faster_whisper.WhisperModel("small", device=device, compute_type=compute_type)
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize Whisper model on {device}: {e}")
                if device == "cuda":
                    logger.warning("NVIDIA GPU (CUDA) initialization failed. Attempting CPU fallback...")
                    try:
                        self._model = faster_whisper.WhisperModel("small", device="cpu", compute_type="int8")
                        self._initialized = True
                        return self._model
                    except Exception as fallback_err:
                        logger.error(f"Whisper CPU fallback failed: {fallback_err}")
                self._model = None
                self._initialized = True  # Set to True so we do not repeatedly throw tracebacks on subsequent calls
        return self._model

    def transcribe_audio(self, audio_path: str) -> str:
        """Transcribe an audio file to text using Gemini API (if available) or faster-whisper.
        Auto-detects language (e.g., Urdu or English).
        Returns a short string or an error message.
        """
        # Convert path to string for os.path check
        path_str = str(audio_path)
        if not os.path.isfile(path_str):
            logger.error(f"Audio not found: {path_str}")
            return "Audio not available."

        # 1. Try Google Gemini Cloud ASR if enabled and key is present
        gemini_client = self._init_gemini()
        if gemini_client:
            try:
                import mimetypes
                from google.genai import types
                from src.utils.api_utils import retry_api_call

                # Guess mime type, fallback to audio/mp3 if unknown
                mime_type, _ = mimetypes.guess_type(path_str)
                if not mime_type:
                    ext = os.path.splitext(path_str)[1].lower()
                    if ext == '.m4a':
                        mime_type = 'audio/m4a'
                    elif ext == '.mp3':
                        mime_type = 'audio/mp3'
                    elif ext == '.wav':
                        mime_type = 'audio/wav'
                    elif ext == '.ogg':
                        mime_type = 'audio/ogg'
                    else:
                        mime_type = 'audio/mpeg'

                logger.info(f"Attempting cloud Gemini audio transcription for {path_str} (mime: {mime_type})...")
                with open(path_str, "rb") as f:
                    audio_bytes = f.read()

                prompt = (
                    "Provide an accurate transcript of the speech in this audio file. "
                    "Preserve bilingual English and Urdu transitions without translating them. "
                    "Return ONLY the transcription text. Do not add any introduction, explanations, or quotes."
                )

                response = retry_api_call(
                    gemini_client.models.generate_content,
                    model='gemini-1.5-flash',
                    contents=[
                        types.Part.from_bytes(
                            data=audio_bytes,
                            mime_type=mime_type
                        ),
                        prompt
                    ]
                )
                
                if response and response.text:
                    transcription = response.text.strip()
                    logger.info(f"Cloud Gemini transcription successful for {path_str}")
                    return transcription
                else:
                    logger.warning("Cloud Gemini transcription returned empty response. Falling back to local Whisper.")
            except Exception as e:
                logger.error(f"Cloud Gemini transcription failed, falling back to local Whisper: {e}")

        # 2. Fallback to local faster-whisper
        model = self._init_whisper()
        if model is None:
            logger.error("Whisper model is not initialized. Audio transcription is unavailable.")
            return "Transcription unavailable."

        try:
            # Omitting language parameter enables Whisper's auto-detection of Urdu and English
            segments, info = model.transcribe(path_str)
            logger.info(f"Transcribed audio (local Whisper): detected language '{info.language}' with probability {info.language_probability:.2f}")
            return " ".join([seg.text for seg in segments]).strip()
        except Exception as e:
            logger.error(f"Audio transcription failed: {e}")
            return "Transcription failed."

media_processor = MediaProcessor()
