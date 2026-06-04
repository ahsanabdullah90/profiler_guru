import os
from datetime import datetime

class StorageManager:
    def __init__(self, base_dir="chats"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_quarter_filename(self, dt):
        quarter = (dt.month - 1) // 3 + 1
        return f"{dt.year}_Q{quarter}.md"

    def get_chat_paths(self, chat_name):
        """
        Structure:
        chats/[chat_name]/Chats/
        chats/[chat_name]/Media/
        chats/[chat_name]/Audio/
        """
        # Sanitize chat_name to prevent path traversal
        safe_chat_name = chat_name.replace("/", "_").replace("\\", "_").replace("\0", "_")
        safe_chat_name = os.path.basename(safe_chat_name)

        chat_root = os.path.abspath(os.path.join(self.base_dir, safe_chat_name))
        base_dir_abs = os.path.abspath(self.base_dir)

        # Strict prefix check
        if not chat_root.startswith(os.path.join(base_dir_abs, '')):
            raise ValueError(f"Invalid chat name: {chat_name}")

        chats_dir = os.path.join(chat_root, "Chats")
        media_dir = os.path.join(chat_root, "Media")
        audio_dir = os.path.join(chat_root, "Audio")

        os.makedirs(chats_dir, exist_ok=True)
        os.makedirs(media_dir, exist_ok=True)
        os.makedirs(audio_dir, exist_ok=True)

        return {
            "chat_root": chat_root,
            "chats_dir": chats_dir,
            "media_dir": media_dir,
            "audio_dir": audio_dir
        }

    def save_message(self, chat_name, sender, text, timestamp, media_type=None, media_local_path=None):
        paths = self.get_chat_paths(chat_name)

        dt = datetime.fromtimestamp(timestamp / 1000.0) if isinstance(timestamp, (int, float)) else timestamp
        filename = self.get_quarter_filename(dt)
        file_path = os.path.join(paths["chats_dir"], filename)

        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        content = f"### [{time_str}] {sender}\n{text}\n"

        if media_type == "image" and media_local_path:
            filename_media = os.path.basename(media_local_path)
            # Relative path from the markdown file to the media
            # markdown is in Chats/, media is in Media/
            # so ../Media/filename
            content += f"![image](../Media/{filename_media})\n"
        elif media_type == "audio" and media_local_path:
            filename_audio = os.path.basename(media_local_path)
            content += f"[Audio](../Audio/{filename_audio})\n"

        content += "\n---\n"

        with open(file_path, "a", encoding='utf-8') as f:
            f.write(content)

        return content, file_path, filename.replace(".md", "")
