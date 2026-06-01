## 2026-06-01 - Path Traversal Protection in StorageManager
**Vulnerability:** Path traversal in `StorageManager.get_chat_paths` allowed arbitrary directory creation by using `..` in `chat_name`.
**Learning:** `os.path.join` with unsanitized user input is dangerous even if it feels like it's restricted to a subfolder. `os.path.abspath` and prefix validation are necessary for robust protection.
**Prevention:** Always sanitize input components (replace '/', '\', and null bytes) and strictly validate that final absolute paths reside within the configured base directory.
