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
        chat_root = os.path.join(self.base_dir, chat_name)
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

    def _format_message(self, sender, text, dt, media_type=None, media_local_path=None):
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        content = f"### [{time_str}] {sender}\n{text}\n"

        if media_type == "image" and media_local_path:
            filename_media = os.path.basename(media_local_path)
            content += f"![image](../Media/{filename_media})\n"
        elif media_type == "audio" and media_local_path:
            filename_audio = os.path.basename(media_local_path)
            content += f"[Audio](../Audio/{filename_audio})\n"

        content += "\n---\n"
        return content

    def save_message(self, chat_name, sender, text, timestamp, media_type=None, media_local_path=None):
        paths = self.get_chat_paths(chat_name)

        dt = datetime.fromtimestamp(timestamp / 1000.0) if isinstance(timestamp, (int, float)) else timestamp
        filename = self.get_quarter_filename(dt)
        file_path = os.path.join(paths["chats_dir"], filename)

        content = self._format_message(sender, text, dt, media_type, media_local_path)

        with open(file_path, "a", encoding='utf-8') as f:
            f.write(content)

        return content, file_path, filename.replace(".md", "")

    def save_messages_batch(self, chat_name, messages_data):
        """
        messages_data: list of dicts with keys: sender, text, timestamp, media_type, media_local_path
        """
        paths = self.get_chat_paths(chat_name)
        groups = {}
        rag_payload = {}

        for msg in messages_data:
            timestamp = msg.get('timestamp')
            dt = datetime.fromtimestamp(timestamp / 1000.0) if isinstance(timestamp, (int, float)) else timestamp
            filename = self.get_quarter_filename(dt)
            quarter_id = filename.replace(".md", "")

            content = self._format_message(
                msg.get('sender'),
                msg.get('text'),
                dt,
                msg.get('media_type'),
                msg.get('media_local_path')
            )

            if filename not in groups:
                groups[filename] = []
            groups[filename].append(content)

            if quarter_id not in rag_payload:
                rag_payload[quarter_id] = []
            rag_payload[quarter_id].append(content)

        for filename, contents in groups.items():
            file_path = os.path.join(paths["chats_dir"], filename)
            with open(file_path, "a", encoding='utf-8') as f:
                f.write("".join(contents))

        final_rag_payload = {qid: "".join(contents) for qid, contents in rag_payload.items()}
        return final_rag_payload
