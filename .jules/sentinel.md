## 2025-05-15 - Path Traversal in Data Import and Storage
**Vulnerability:** Path traversal vulnerabilities were found in `StorageManager` (via `chat_name`) and `InstagramDataImporter` (via `photo['uri']` and `audio['uri']` in export JSON).
**Learning:** User-controlled strings used in file path construction MUST be sanitized and validated against an absolute base directory using `os.path.abspath` and `startswith`.
**Prevention:** Always use `os.path.normpath` and verify that the absolute path of the target file/directory starts with the absolute path of the intended parent directory.
