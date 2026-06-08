## 2026-06-08 - [Batched ChromaDB Indexing]
**Learning:** ChromaDB indexing performance improves significantly (measured ~9x speedup) when using batched `upsert` operations compared to individual calls. Using stable MD5 hashes for IDs ensures idempotency.
**Action:** Always batch vector database operations when processing multiple records (e.g., during bulk imports or multi-message syncs).
