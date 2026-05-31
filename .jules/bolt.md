## 2025-05-14 - Batching ChromaDB indexing and stable hashing

**Learning:** Batching ChromaDB `upsert` operations significantly reduces indexing overhead during bulk imports. In this application, moving from individual message indexing to batches of 50 reduces the number of database calls by 50x. Additionally, using `hashlib.md5` for document IDs instead of Python's `hash()` ensures idempotency across process restarts, which is critical for a sync-based application.

**Action:** Always batch vector database operations when processing large datasets. Use stable hashing for IDs to maintain consistency and avoid duplicates during re-syncs.
