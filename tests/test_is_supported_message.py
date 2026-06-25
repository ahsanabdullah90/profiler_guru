# tests/test_is_supported_message.py
from src.engine.instagram_sync import is_supported_message
from src.engine.data_importer import is_supported_json_message

class MockAttachment:
    def __init__(self, type, url=""):
        self.type = type
        self.payload = {"url": url}

class MockDirectMessage:
    def __init__(self, item_type, text="", attachments=None):
        self.item_type = item_type
        self.text = text
        self.attachments = attachments or []
        self.id = "mock_msg_id"

def test_live_sync_is_supported_message():
    # 1. Text message -> Supported
    msg = MockDirectMessage(item_type="text", text="Hello there")
    assert is_supported_message(msg) is True
    
    # 2. Voice media message -> Supported
    msg = MockDirectMessage(item_type="voice_media")
    assert is_supported_message(msg) is True
    
    # 3. Clip/Reel share -> Unsupported
    msg = MockDirectMessage(item_type="clip")
    assert is_supported_message(msg) is False
    msg = MockDirectMessage(item_type="reel_share")
    assert is_supported_message(msg) is False
    
    # 4. Text containing reel link -> Unsupported
    msg = MockDirectMessage(item_type="text", text="Check this out: https://www.instagram.com/reel/C82B57/")
    assert is_supported_message(msg) is False
    
    # 5. Attachment audio -> Supported
    msg = MockDirectMessage(item_type="media", attachments=[MockAttachment(type="audio", url="https://instagram.cdn/voice.mp4")])
    assert is_supported_message(msg) is True
    
    # 6. Attachment reel -> Unsupported
    msg = MockDirectMessage(item_type="media", attachments=[MockAttachment(type="reel")])
    assert is_supported_message(msg) is False
    
    # 7. Attachment video/image without voice -> Unsupported
    msg = MockDirectMessage(item_type="media", attachments=[MockAttachment(type="video", url="https://instagram.cdn/movie.mp4")])
    assert is_supported_message(msg) is False

def test_json_import_is_supported_json_message():
    # 1. Text message -> Supported
    msg = {"content": "Hello there"}
    assert is_supported_json_message(msg) is True
    
    # 2. Audio message -> Supported
    msg = {"content": "", "audio_files": [{"uri": "audio/clip.mp4"}]}
    assert is_supported_json_message(msg) is True
    
    # 3. Reel share -> Unsupported
    msg = {"content": "", "share": {"link": "https://www.instagram.com/reel/C82B57/"}}
    assert is_supported_json_message(msg) is False
    
    # 4. Content containing reel link -> Unsupported
    msg = {"content": "Check this out: https://www.instagram.com/reels/C82B57/"}
    assert is_supported_json_message(msg) is False
    
    # 5. Media message (photo/video without audio) -> Unsupported
    msg = {"content": "", "photos": [{"uri": "photo.jpg"}]}
    assert is_supported_json_message(msg) is False
    msg = {"content": "", "videos": [{"uri": "video.mp4"}]}
    assert is_supported_json_message(msg) is False
