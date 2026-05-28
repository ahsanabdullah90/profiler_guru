## 2025-06-25 - Path Traversal in Storage Manager
**Vulnerability:** Path traversal in `StorageManager.get_chat_paths` via `chat_name` parameter.
**Learning:** External data (like Instagram thread titles) used in file paths can lead to path traversal if not sanitized, allowing attackers to create or manipulate files outside the intended base directory.
**Prevention:** Always sanitize user-provided or external identifiers used in file system operations. Replace slashes ('/' and '\') and use `os.path.basename()` to ensure the identifier does not contain path components.
