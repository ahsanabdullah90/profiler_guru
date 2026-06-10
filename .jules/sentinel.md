## 2026-06-10 - Path Traversal in Export-based Importers
**Vulnerability:** User-controlled relative paths in Instagram export JSON (e.g., `photo['uri']`) were used directly with `os.path.join(export_path, ...)` to copy files.
**Learning:** Even with a trusted base path, relative paths in data files can escape the intended directory. Sanitization alone isn't enough; absolute path validation is required.
**Prevention:** Always use `os.path.abspath()` on both the base directory and the final path, then verify the final path starts with the base directory path (including a trailing separator for strict prefix matching).
