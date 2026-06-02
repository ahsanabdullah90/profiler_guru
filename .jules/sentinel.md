## 2025-05-15 - Path Traversal Protection in StorageManager
**Vulnerability:** Path traversal was possible via the `chat_name` parameter in `StorageManager.get_chat_paths`, allowing creation of directories outside the intended `base_dir`.
**Learning:** Even when using `os.path.join`, unsanitized user input containing `..` can escape the base directory. Simply replacing `/` and `\` is not enough if `..` is still allowed, as it can be part of a filename.
**Prevention:**
1. Sanitize all path components by replacing dangerous characters: `/`, `\`, `\0`, and especially `..`.
2. Use `os.path.basename()` as a secondary defense to ensure only the final component is used.
3. Use absolute path comparison with a trailing separator to strictly validate that the final path resides within the base directory.
