# Bolt's Journal - InstaSync AI

## 2025-05-15 - [Batched ChromaDB Indexing]
**Learning:** ChromaDB `upsert` operations have significant overhead when called individually for each message. Batching these calls (e.g., batch size of 50) dramatically reduces IO and computation overhead, especially when using default embedding functions.
**Action:** Always prefer batched indexing (`add_messages_batch`) for bulk data imports or sync operations where multiple messages are processed at once.

**Measured Impact:**
- Individual indexing: ~326ms per message
- Batched indexing (size 50): ~36ms per message
- Total speedup: ~9x
