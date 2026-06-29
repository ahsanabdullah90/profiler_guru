# tests/test_is_supported_message.py
from src.engine.data_importer import is_supported_json_message

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
