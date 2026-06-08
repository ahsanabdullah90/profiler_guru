## 2026-06-08 - Path Traversal in Storage and Importer
**Vulnerability:** Path traversal via unsanitized `chat_name` in `StorageManager` and `uri` in `InstagramDataImporter`.
**Learning:** External data from Instagram exports (JSON files) can contain malicious relative paths that lead to reading or writing files outside of the intended directories. Even seemingly internal names like `chat_name` can be manipulated if they are derived from external data.
**Prevention:** Always use `os.path.basename()` to sanitize filenames, and use `os.path.abspath()` combined with `startswith()` against an absolute base directory to ensure paths stay within bounds. Fixed common `ImportError` in `media_processor` usage which was discovered during security testing.
