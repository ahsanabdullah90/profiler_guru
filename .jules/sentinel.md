## 2026-06-11 - [Path Traversal in Export Importers]
**Vulnerability:** Path traversal via user-controlled `uri` fields in Instagram export JSON files, allowing attackers to copy arbitrary files from the server into the application's storage.
**Learning:** `os.path.join` with an absolute path as a component can be dangerous, and `startswith` checks on paths can be bypassed if sibling directories share a common prefix.
**Prevention:** Always use `os.path.abspath` on both the base and resolved paths, and ensure the base path has a trailing separator for strict prefix matching during validation. Also, sanitize all user-controlled path components using `os.path.basename` and character replacement.
