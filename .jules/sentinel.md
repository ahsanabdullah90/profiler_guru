2025-06-25 - [Path Traversal in StorageManager]
Identified and fixed a path traversal vulnerability in StorageManager.get_chat_paths where unsanitized chat_name could be used to create directories outside the base_dir.
Mitigation: Replaced traversal characters, used os.path.basename, and validated final absolute path prefix.
