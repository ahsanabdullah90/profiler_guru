## 2025-05-15 - [Batched ChromaDB Indexing]
**Learning:** Individual `upsert` operations in ChromaDB are a major bottleneck due to I/O and transaction overhead. Batching these operations (e.g., size 50) can yield nearly 9x performance improvement. Additionally, using `hashlib.md5` for document IDs ensures idempotency across application restarts, preventing duplicate indexing of the same content.
**Action:** Always prefer batched indexing for bulk data imports or high-frequency synchronization tasks. Use deterministic hashing for IDs to maintain index consistency and avoid duplicates.
