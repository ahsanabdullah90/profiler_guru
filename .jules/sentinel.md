## 2025-05-22 - [Path Traversal in StorageManager]
**Vulnerability:** User-controlled chat names could contain path traversal sequences (e.g., `../`), allowing arbitrary file writes outside the intended `chats/` directory.
**Learning:** Using `os.path.join` with unsanitized user input is dangerous. Even if the base directory is fixed, `../` can escape it.
**Prevention:** Sanitize input by replacing directory separators and validate the final absolute path against the absolute base directory.

## 2025-05-22 - [Non-deterministic ID generation in RAG]
**Vulnerability:** Using Python's built-in `hash()` function for database IDs leads to non-deterministic behavior across process restarts, potentially causing duplicate entries or lookup failures in persistent storage like ChromaDB.
**Learning:** `hash()` in Python 3 is salted and changes per session by default.
**Prevention:** Use stable hashing algorithms like `hashlib.sha256` or `hashlib.md5` for persistent IDs.
