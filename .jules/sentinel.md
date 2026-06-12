## 2026-06-12 - [Path Traversal in Export Importers]
**Vulnerability:** Path traversal via unsanitized chat names and media URIs in Instagram JSON exports.
**Learning:** Export data often contains relative or absolute paths (e.g., `photo['uri']`) that can be manipulated by an attacker to access sensitive files outside the export directory or store data in unauthorized locations.
**Prevention:** Always validate user-provided paths against an absolute base directory using `.startswith(os.path.join(base_dir_abs, ''))` and sanitize path components (replacing `..`, `/`, `\`) before constructing file system paths.
