## 2025-05-15 - Batch RAG indexing optimization
**Learning:** ChromaDB performance is heavily sensitive to batching. Transitioning from individual `upsert` calls to batches of 50 yielded a ~9.3x speedup. Additionally, using `hashlib.md5` for document IDs ensures idempotency and prevents duplicate entries across app restarts compared to the non-stable `hash()` function.
**Action:** Always prefer `add_messages_batch` for bulk imports or sync operations and use stable hashing for vector store IDs.
