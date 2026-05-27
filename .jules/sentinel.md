## 2025-06-25 - [Path Traversal in StorageManager]
**Vulnerability:** The `StorageManager.get_chat_paths` method was using the `chat_name` (derived from Instagram thread titles) directly in `os.path.join`, allowing for potential path traversal.
**Learning:** Even internal names from APIs like Instagram should be treated as untrusted, especially when used for file system operations. Basename isn't always enough if the path separators differ between the attacker's input and the OS.
**Prevention:** Always sanitize filenames by replacing both `/` and `\` separators and checking against common navigation patterns (`..`, `.`).
