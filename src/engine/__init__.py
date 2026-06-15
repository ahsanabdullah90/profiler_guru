from src.engine.media_processor import describe_image, transcribe_audio

class MediaProcessor:
    def describe_image(self, image_path):
        return describe_image(image_path)
    def transcribe_audio(self, audio_path):
        return transcribe_audio(audio_path)

media_processor = MediaProcessor()
