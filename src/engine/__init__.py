from .media_processor import describe_image, transcribe_audio
from .rag_engine import rag_engine
from .data_importer import InstagramDataImporter
from .instagram_sync import InstagramSync

# Export media processor functions under a common namespace object to avoid
# breaking existing code that expects 'media_processor.function_name'
class MediaProcessor:
    @staticmethod
    def describe_image(path):
        return describe_image(path)

    @staticmethod
    def transcribe_audio(path):
        return transcribe_audio(path)

media_processor = MediaProcessor()

__all__ = [
    "media_processor",
    "rag_engine",
    "InstagramDataImporter",
    "InstagramSync"
]
