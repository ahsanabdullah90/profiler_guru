## 2025-05-15 - [Stable Hashing for RAG IDs]
**Learning:** ChromaDB indexing IDs should never use the built-in Python `hash()` function if they need to be persistent across process restarts. `hash()` is salted and non-deterministic between different Python executions, leading to duplicate entries and broken RAG lookups after a restart.
**Action:** Always use a stable hashing algorithm like `hashlib.md5()` for generating IDs that are stored in a persistent vector database.

## 2025-05-15 - [ChromaDB Batching Speedup]
**Learning:** Individual `upsert` calls to ChromaDB for every message are extremely slow due to the overhead of IO and indexing for each call.
**Action:** Implement batched indexing (e.g., batch size of 50) in `RAGEngine` to achieve significant (up to 7-8x) performance improvements during bulk data import and synchronization.
