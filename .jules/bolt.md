## 2025-05-29 - [Batch ChromaDB Indexing]
**Learning:** Indexing documents one-by-one in ChromaDB is a major bottleneck due to I/O and overhead per operation. Batching multiple `upsert` calls into a single operation can yield massive speedups (e.g., >5x improvement in import times). Also, using Python's built-in `hash()` for IDs is dangerous as it is process-randomized, leading to duplicate entries upon restart; `hashlib.md5` provides the necessary stability.
**Action:** Always prefer `upsert` with multiple documents. Use stable hashing (MD5/SHA) for document IDs to ensure idempotency.
