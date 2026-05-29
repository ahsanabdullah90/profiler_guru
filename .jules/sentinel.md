## 2025-05-22 - Path Traversal in Storage Management
**Vulnerability:** User-controlled `chat_name` was used directly in `os.path.join` to construct file system paths, allowing for path traversal (e.g., `../`).
**Learning:** Even if the input is expected to be from a trusted source (like an API), sanitizing it before use in file system operations is critical.
**Prevention:** Use `os.path.basename()` and validate the resulting absolute path against the intended base directory using a trailing separator for strict prefix matching.
