## 2025-05-22 - Path Traversal in StorageManager
**Vulnerability:** Path traversal via `chat_name` parameter in `StorageManager.get_chat_paths`.
**Learning:** User-provided chat names were used directly in `os.path.join`, allowing directory escape via `..`. Sanitization must include replacing separators ('/', '\') and null bytes, followed by `os.path.basename` and strict prefix matching of the absolute path.
**Prevention:** Use a dedicated sanitization helper for all path components derived from external input and validate against a base directory using `os.path.abspath`.
