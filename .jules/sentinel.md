## 2025-05-15 - Path Traversal Prevention in Storage Management
**Vulnerability:** Path traversal in `StorageManager.get_chat_paths` allowed attackers to create directories and files outside the intended `chats/` root by providing malicious `chat_name` inputs like `../evil`.
**Learning:** Simple `basename` sanitization is often insufficient if the application logic later joins that result with other components. A robust solution requires absolute path resolution and a strict prefix check.
**Prevention:** Use `os.path.abspath()` on both the base directory and the target path, then verify the target path `startswith` the base directory (ensuring the base directory has a trailing separator to prevent partial prefix matches like `/data` matching `/database`).
