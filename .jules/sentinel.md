## 2025-06-25 - Path Traversal in Storage Manager
**Vulnerability:** Path traversal via unsanitized `chat_name` in `StorageManager.get_chat_paths`.
**Learning:** Using `os.path.join` with user-provided components without sanitization allows directory creation outside the intended base directory. Even if `chat_name` is a "name", it can contain traversal characters like `..`.
**Prevention:** Sanitize path components by replacing separators (`/`, `\`) and null bytes (`\0`) with underscores. Additionally, validate the resulting absolute path against the absolute base directory with a strict prefix check (using a trailing separator for exact match).
