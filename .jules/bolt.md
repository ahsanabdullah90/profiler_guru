## 2025-05-22 - [Batched Vector Database Indexing]
**Learning:** ChromaDB `upsert` operations have significant overhead when called individually. Batching messages into groups (e.g., size 50) provides a ~8-9x speedup during bulk imports and synchronization. Using a deterministic hashing (like MD5) for IDs instead of Python's `hash()` is critical for idempotency and avoiding duplicates across sessions.
**Action:** Always prefer `add_messages_batch` for bulk operations and ensure ID generation is stable.

## 2025-05-22 - [Deterministic ID Generation]
**Learning:** Using Python's built-in `hash()` function for database IDs leads to non-deterministic results across process restarts (due to hash randomization). This causes duplicate entries in the vector database when re-indexing the same data.
**Action:** Use `hashlib.md5` or similar stable hashing algorithms for generating content-based IDs in persistent storage.
