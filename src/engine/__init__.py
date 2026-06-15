from .media_processor import describe_image, transcribe_audio
from .rag_engine import RAGEngine

class MediaProcessorShim:
    def describe_image(self, *args, **kwargs):
        return describe_image(*args, **kwargs)
    def transcribe_audio(self, *args, **kwargs):
        return transcribe_audio(*args, **kwargs)

media_processor = MediaProcessorShim()
rag_engine = RAGEngine()
