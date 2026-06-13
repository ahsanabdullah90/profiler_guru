## 2025-05-15 - [Path Traversal in Instagram Data Importer and Storage Manager]
**Vulnerability:** Path traversal via unsanitized `chat_name` in `StorageManager` and `uri` in `InstagramDataImporter`.
**Learning:** Instagram exports and live sync threads can provide malicious filenames or relative paths that escape the intended storage directory if not strictly validated against an absolute base path.
**Prevention:** Use `os.path.normpath` followed by `os.path.abspath` to resolve paths, and then verify that the absolute path starts with the absolute base directory (with a trailing separator for strictness). Additionally, use `os.path.basename` to sanitize user-provided directory names.
