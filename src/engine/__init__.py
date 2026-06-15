from .media_processor import describe_image, transcribe_audio

class MediaProcessor:
    def describe_image(self, path):
        return describe_image(path)
    def transcribe_audio(self, path):
        return transcribe_audio(path)

media_processor = MediaProcessor()
