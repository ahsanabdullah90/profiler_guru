## 2026-06-12 - [RAG Indexing Batching]
**Learning:** ChromaDB indexing performance is significantly bottlenecked by individual `upsert` calls due to overhead per transaction/operation. Hashing document contents for IDs also prevents duplicates and improves efficiency.
**Action:** Always batch RAG indexing operations (e.g., batch size 50-100) when importing or syncing large amounts of data. Use stable hashes (MD5) for IDs to ensure idempotency.
