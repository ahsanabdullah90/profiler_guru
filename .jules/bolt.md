## 2026-05-27 - [ChromaDB Batching & Idempotency]
**Learning:** ChromaDB `upsert` and `add` operations are significantly faster when batched. However, when implementing batching, document ID generation MUST remain deterministic (e.g., using hashing) to ensure idempotency. Avoid using Python's `hash()` (process-randomized) or `os.urandom()` for database IDs, as they lead to data duplication on re-imports.
**Action:** Always use a stable hashing algorithm like `hashlib.md5` or `hashlib.sha256` for generating content-based IDs, and batch database writes where possible for performance.
