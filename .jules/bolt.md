## 2025-05-14 - [Batch Indexing and ID Stability]
**Learning:** Batching ChromaDB upsert operations significantly reduces IO overhead and improves performance during large data imports. Additionally, using stable hashing (like MD5) for document IDs is critical for idempotency and avoids duplicates across restarts, as Python's default `hash()` is randomized.
**Action:** Always prefer `add_messages_batch` for bulk imports and use `hashlib` for persistent record identifiers.
