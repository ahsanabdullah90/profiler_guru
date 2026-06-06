## 2026-06-06 - [Path Traversal in StorageManager]
**Vulnerability:** Path traversal via `chat_name` in `StorageManager.get_chat_paths`. An attacker could provide a `chat_name` like `../evil` to create directories outside the intended `chats/` base directory.
**Learning:** Using `os.path.join` with user-supplied input without sanitization or absolute path validation is insufficient to prevent directory escape.
**Prevention:** Sanitize input by replacing path separators (`/`, `\`) and null bytes, use `os.path.basename`, and perform a strict prefix check on the absolute path of the final destination against the absolute path of the base directory.
