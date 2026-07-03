import hashlib
import os
import re
import threading

import chromadb
from chromadb.utils import embedding_functions
from google import genai

from src.utils.config import config
from src.utils.logger import logger
from src.utils.markdown import filter_month_files, parse_message_blocks
from src.utils.redis_client import cache_get, cache_set

# Define the default embedding function (all-MiniLM-L6-v2, dimension 384)
default_ef = embedding_functions.DefaultEmbeddingFunction()

_CHUNK_ID_RE = re.compile(r'<!--\s*chunk_id:\s*([a-f0-9]+)\s*-->')

def chunk_text(text: str, max_chars: int = 2000, overlap: int = 200) -> list:
    """Splits text into chunks of max_chars with overlap, avoiding cutting words if possible."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = start + max_chars
        if end >= text_len:
            chunks.append(text[start:])
            break

        # Try to find a clean boundary (newline or space) near the end
        boundary = text.rfind('\n', start + max_chars - 100, end)
        if boundary == -1:
            boundary = text.rfind(' ', start + max_chars - 50, end)

        if boundary != -1 and boundary > start:
            end = boundary

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start >= text_len - overlap:
            break

    return chunks

def extract_date_range(chunk: str) -> str:
    """Extracts the first and last timestamps from the chunk using regex."""
    # Matches format [YYYY-MM-DD HH:MM:SS]
    timestamps = re.findall(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', chunk)
    if not timestamps:
        return "unknown"
    if len(timestamps) == 1:
        return str(timestamps[0])
    return f"{timestamps[0]} to {timestamps[-1]}"


class RAGEngine:
    def __init__(self, db_path: str | None = None):
        self._lock = threading.RLock()
        self._lock_timeout = 5  # seconds
        self.db_path = db_path if db_path is not None else str(config.DATA_DIR / "chroma_db")
        self.client = chromadb.PersistentClient(path=self.db_path)

        if config.GOOGLE_API_KEY:
            self.gemini_client = genai.Client(api_key=config.GOOGLE_API_KEY)
        else:
            self.gemini_client = None

        # Initialize the collection with the explicit embedding function
        self.collection = self.client.get_or_create_collection(
            name="instagram_messages",
            metadata={"hnsw:space": "cosine"},
            embedding_function=default_ef
        )

        # Pre-flight check: validate embedding dimension consistency
        self._validate_embedding_dimension()

    def _validate_embedding_dimension(self):
        """Checks if the existing ChromaDB collection dimension matches the embedding function (384).
        If a mismatch occurs (e.g. from an old or corrupt db), deletes and recreates it.
        """
        try:
            # Peek at an element to trigger dimension validation checks
            self.collection.peek(limit=1)
            logger.info("ChromaDB embedding dimension validated successfully.")
        except Exception as e:
            if "dimension" in str(e).lower() or "mismatch" in str(e).lower():
                logger.warning("ChromaDB embedding dimension mismatch detected. Recreating collection for consistency...")
                try:
                    self.client.delete_collection(name="instagram_messages")
                    self.collection = self.client.get_or_create_collection(
                        name="instagram_messages",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=default_ef
                    )
                    logger.info("Collection successfully recreated.")
                except Exception as del_err:
                    logger.error(f"Failed to recreate collection: {del_err}")
            else:
                logger.debug(f"ChromaDB collection peek info: {e}")

    def add_messages_batch(self, batch_data):
        """
        batch_data: list of (chat_name, month, messages_text)
        Splits text into 2000-character chunks with a 200-character overlap before indexing.
        """
        all_chunks = []
        all_metadatas = []
        all_ids = []
        seen_ids = set()

        for chat_name, month, messages_text in batch_data:
            # Clean and split into conversational message blocks
            raw_blocks = parse_message_blocks(messages_text)
            reconstructed_text = "\n---\n".join(raw_blocks)

            # Apply sliding window chunking
            chunks = chunk_text(reconstructed_text, max_chars=2000, overlap=200)

            for idx, chunk in enumerate(chunks):
                # Try to extract stable chunk_id comment from the block
                chunk_id_match = _CHUNK_ID_RE.search(chunk)
                if chunk_id_match:
                    base_id = chunk_id_match.group(1)
                    doc_id = f"{chat_name}_{month}_{base_id}_{idx}"[:100]
                else:
                    # Legacy fallback: MD5 of content (pre-chunk-ID messages)
                    content_hash = hashlib.md5(chunk.encode('utf-8')).hexdigest()
                    doc_id = f"{chat_name}_{month}_{content_hash}_{idx}"[:100]

                # Defensive check: skip duplicate IDs within the same upsert batch to prevent ChromaDB crash
                if doc_id in seen_ids:
                    logger.warning(f"Skipping duplicate ID '{doc_id}' in batch upsert.")
                    continue
                seen_ids.add(doc_id)

                all_chunks.append(chunk)
                date_range = extract_date_range(chunk)
                all_metadatas.append({
                    "chat_name": chat_name,
                    "month": month,
                    "date_range": date_range,
                    "chunk_index": idx
                })
                all_ids.append(doc_id)

        if not all_chunks:
            return

        if not self._lock.acquire(timeout=self._lock_timeout):
            logger.warning("ChromaDB lock timeout on add_messages_batch — skipping")
            return
        try:
            self.collection.upsert(
                documents=all_chunks,
                metadatas=all_metadatas,
                ids=all_ids
            )
        finally:
            self._lock.release()

    def add_messages_to_index(self, chat_name, month, messages_text):
        self.add_messages_batch([(chat_name, month, messages_text)])

    def update_transcribed_message(self, chat_name: str, month: str, old_text: str, new_text: str):
        """Updates a message chunk in the vector store after transcription.
        Preferentially uses the stable chunk_id comment for deletion;
        falls back to MD5-of-content for legacy blocks without a comment.
        """
        # 1. Try to extract stable chunk_id(s) from the old block
        stable_ids = _CHUNK_ID_RE.findall(old_text)

        # 1. Resolve block structure and chunk the old text
        raw_blocks_old = parse_message_blocks(old_text)
        reconstructed_old = "\n---\n".join(raw_blocks_old)
        chunks_old = chunk_text(reconstructed_old, max_chars=2000, overlap=200)

        if stable_ids:
            # Build deletion IDs from the stable chunk IDs
            old_ids = [
                f"{chat_name}_{month}_{stable_ids[0]}_{idx}"[:100]
                for idx in range(len(chunks_old))
            ]
        else:
            # Legacy fallback: recompute MD5 hashes from content
            old_ids = [
                f"{chat_name}_{month}_{hashlib.md5(c.encode('utf-8')).hexdigest()}_{idx}"[:100]
                for idx, c in enumerate(chunks_old)
            ]

        # 2. Delete old documents from ChromaDB
        if old_ids:
            if self._lock.acquire(timeout=self._lock_timeout):
                try:
                    self.collection.delete(ids=old_ids)
                    logger.info(f"Deleted {len(old_ids)} old placeholder chunks for {chat_name} ({month}) in ChromaDB.")
                except Exception as e:
                    logger.error(f"Failed to delete old placeholder chunks: {e}")
                finally:
                    self._lock.release()
            else:
                logger.warning(f"ChromaDB lock timeout on delete for {chat_name}")

        # 3. Index the new transcribed message block
        self.add_messages_batch([(chat_name, month, new_text)])

    def vacuum_orphaned_vectors(self) -> int:
        """Scans all markdown files and removes ChromaDB vectors with no corresponding disk block.
        Returns the count of deleted orphan IDs.
        Uses a dual-index approach (stable chunk_ids + legacy MD5 hashes) to avoid valid data deletion.
        """
        import os

        # 1. Collect all active IDs from disk
        active_ids: set[str] = set()
        chats_root = config.CHATS_DIR
        if not os.path.exists(chats_root):
            return 0

        for contact in os.listdir(chats_root):
            chats_dir = os.path.join(chats_root, contact, "Chats")
            if not os.path.isdir(chats_dir):
                continue
            for fname in os.listdir(chats_dir):
                if not fname.endswith(".md"):
                    continue
                month = fname[:-3]
                fpath = os.path.join(chats_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = f.read()
                    raw_blocks = [b.strip() for b in content.split("---") if b.strip()]
                    for block in raw_blocks:
                        chunks = chunk_text(block, max_chars=2000, overlap=200)
                        for idx, chunk in enumerate(chunks):
                            match = _CHUNK_ID_RE.search(chunk)
                            if match:
                                doc_id = f"{contact}_{month}_{match.group(1)}_{idx}"[:100]
                            else:
                                doc_id = f"{contact}_{month}_{hashlib.md5(chunk.encode()).hexdigest()}_{idx}"[:100]
                            active_ids.add(doc_id)
                except Exception as e:
                    logger.error(f"vacuum_orphaned_vectors: failed reading {fpath}: {e}")

        # 2. Fetch all IDs from ChromaDB
        if not self._lock.acquire(timeout=self._lock_timeout):
            logger.warning("ChromaDB lock timeout on vacuum fetch — skipping")
            return 0
        try:
            all_data = self.collection.get(include=[])
            chroma_ids = set(all_data.get("ids", []))
        except Exception as e:
            logger.error(f"vacuum_orphaned_vectors: ChromaDB fetch failed: {e}")
            return 0
        finally:
            self._lock.release()

        # 3. Find and delete orphans in batches of 100
        orphan_ids = list(chroma_ids - active_ids)
        if not orphan_ids:
            logger.info("vacuum_orphaned_vectors: no orphans found.")
            return 0

        deleted = 0
        for i in range(0, len(orphan_ids), 100):
            batch = orphan_ids[i:i + 100]
            if not self._lock.acquire(timeout=self._lock_timeout):
                logger.warning("ChromaDB lock timeout on vacuum delete batch — stopping")
                break
            try:
                self.collection.delete(ids=batch)
                deleted += len(batch)
            except Exception as e:
                logger.error(f"vacuum_orphaned_vectors: delete batch failed: {e}")
            finally:
                self._lock.release()

        logger.info(f"vacuum_orphaned_vectors: deleted {deleted} orphaned vectors.")
        return deleted

    def get_indexed_count(self, chat_name: str) -> int:
        """Retrieves the total count of indexed chunks in ChromaDB for a specific contact."""
        try:
            results = self.collection.get(
                where={"chat_name": chat_name},
                include=[]
            )
            return len(results.get("ids", []))
        except Exception as e:
            logger.error(f"Failed to query indexed count for '{chat_name}': {e}")
            return 0

    def get_all_indexed_counts(self, contacts: list[str] | None = None) -> dict:
        """Returns {chat_name: count} for all contacts in ChromaDB.
        Uses collection.count() with small batches to stay well below ChromaDB's
        SQLite "too many SQL variables" limit. If a batch fails, it is split in
        half and retried recursively before falling back to per-contact counts.
        """
        import os

        # Try cache first
        cache_key = "contacts:index_counts"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        # 1. Resolve the list of contacts if not explicitly provided
        if not contacts:
            contacts = []
            chats_root = config.CHATS_DIR
            if os.path.exists(chats_root):
                try:
                    contacts = [
                        d for d in os.listdir(chats_root)
                        if os.path.isdir(os.path.join(chats_root, d))
                    ]
                except Exception as e:
                    logger.error(f"get_all_indexed_counts: failed to list chats dir: {e}")

        counts = {name: 0 for name in contacts}

        def _count_batch(batch: list[str]) -> None:
            """Try to count a batch; split and retry on SQLite variable limit."""
            if not batch:
                return
            if len(batch) == 1:
                name = batch[0]
                counts[name] = self.get_indexed_count(name)
                return
            try:
                results = self.collection.get(
                    where={"chat_name": {"$in": batch}},
                    include=["metadatas"]
                )
                for meta in results.get("metadatas", []):
                    if meta and "chat_name" in meta:
                        name = meta["chat_name"]
                        if name in counts:
                            counts[name] += 1
            except Exception as e:
                # If the batch is too large for SQLite's variable limit, split it.
                if "too many SQL variables" in str(e) and len(batch) > 1:
                    mid = len(batch) // 2
                    _count_batch(batch[:mid])
                    _count_batch(batch[mid:])
                else:
                    logger.warning(
                        f"get_all_indexed_counts: batch query failed for {len(batch)} contacts: {e}. "
                        "Falling back to individual counts."
                    )
                    for name in batch:
                        counts[name] = self.get_indexed_count(name)

        # Batch size of 20 stays comfortably under SQLite limits in most cases.
        batch_size = 20
        for i in range(0, len(contacts), batch_size):
            _count_batch(contacts[i:i + batch_size])

        cache_set(cache_key, counts)
        return counts



    def fetch_markdown_snippets(self, chat_name: str, start_month: str | None = None, end_month: str | None = None) -> str:
        """Retrieves and merges markdown conversation snippets from the monthly logs,
        filtered by start and end month (inclusive).
        """
        chats_dir = config.CHATS_DIR / chat_name / "Chats"
        if not chats_dir.exists():
            logger.warning(f"Chats directory does not exist for contact '{chat_name}' at {chats_dir}")
            return ""

        md_files = sorted([f for f in os.listdir(chats_dir) if f.endswith(".md")])
        snippets = []

        filtered = filter_month_files(md_files, start_month, end_month)
        for file in filtered:

            file_path = chats_dir / file
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        snippets.append(content)
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")

        return "\n---\n".join(snippets)

    def estimate_token_count(self, text: str) -> int:
        """Counts tokens in the text using tiktoken, falling back to a character heuristic if unavailable."""
        try:
            import tiktoken
            if not hasattr(self, '_tiktoken_encoding'):
                self._tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
            return len(self._tiktoken_encoding.encode(text))
        except Exception as e:
            logger.warning(f"Failed to count tokens using tiktoken (falling back to heuristic): {e}")
            return int(len(text) // config.TOKEN_ESTIMATION_FACTOR)

from src.utils.lazy_proxy import LazyProxy

rag_engine = LazyProxy(RAGEngine)
