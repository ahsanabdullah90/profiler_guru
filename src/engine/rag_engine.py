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

def get_embedding_function(provider: str, model_name: str, host: str = "http://localhost:11434"):
    """Returns the matching ChromaDB embedding function based on configuration."""
    if provider == "ollama":
        logger.info(f"Initializing OllamaEmbeddingFunction with model: {model_name} on host: {host}")
        return embedding_functions.OllamaEmbeddingFunction(
            model_name=model_name,
            url=f"{host}/api/embeddings"
        )
    else:
        logger.info("Initializing Default local SentenceTransformer embedding function (all-MiniLM-L6-v2)")
        return embedding_functions.DefaultEmbeddingFunction()

# Keep default_ef as fallback or legacy reference
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


def chunk_block_respecting_boundaries(block: str, max_chars: int = 2000, overlap: int = 200) -> list[str]:
    """Splits a single message block into sub-chunks if it exceeds max_chars,
    preserving context and the chunk_id comment in each sub-chunk if present.
    """
    chunk_id_match = _CHUNK_ID_RE.search(block)
    chunk_id_comment = f"<!-- chunk_id: {chunk_id_match.group(1)} -->\n" if chunk_id_match else ""
    cleaned_block = _CHUNK_ID_RE.sub("", block).strip()

    if len(cleaned_block) <= max_chars:
        return [cleaned_block + f"\n{chunk_id_comment}" if chunk_id_comment else cleaned_block]

    sub_chunks = []
    start = 0
    text_len = len(cleaned_block)

    while start < text_len:
        end = start + max_chars
        if end >= text_len:
            sub_chunks.append(cleaned_block[start:] + (f"\n{chunk_id_comment}" if chunk_id_comment else ""))
            break

        boundary = cleaned_block.rfind('\n', start + max_chars - 100, end)
        if boundary == -1:
            boundary = cleaned_block.rfind(' ', start + max_chars - 50, end)

        if boundary != -1 and boundary > start:
            end = boundary

        chunk = cleaned_block[start:end].strip()
        if chunk:
            sub_chunks.append(chunk + (f"\n{chunk_id_comment}" if chunk_id_comment else ""))

        start = end - overlap
        if start >= text_len - overlap:
            break

    return sub_chunks


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

        if config.EMBEDDING_PROVIDER == "ollama":
            # Pre-flight check: is the Ollama model installed?
            from src.utils.ollama_client import ollama_client
            installed = ollama_client.get_installed_models()
            if installed:
                match = any(config.EMBEDDING_MODEL in m or m in config.EMBEDDING_MODEL for m in installed)
                if not match:
                    logger.error(f"CRITICAL: Ollama embedding model '{config.EMBEDDING_MODEL}' is not installed! "
                                 f"Please run: 'ollama pull {config.EMBEDDING_MODEL}' on your system.")
            else:
                logger.warning(f"Ollama server appears offline or unreachable at startup. "
                               f"Please make sure Ollama is running and has the '{config.EMBEDDING_MODEL}' model pulled.")

        self.embedding_function = get_embedding_function(
            provider=config.EMBEDDING_PROVIDER,
            model_name=config.EMBEDDING_MODEL,
            host=config.OLLAMA_HOST
        )

        # Initialize the collection with the explicit embedding function
        self.collection = self.client.get_or_create_collection(
            name="instagram_messages",
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function
        )

        self.recreated = False
        # Pre-flight check: validate embedding dimension consistency
        self._validate_embedding_dimension()

    def _validate_embedding_dimension(self):
        """Checks if the existing ChromaDB collection dimension matches the embedding function.
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
                    self.recreated = True
                    self.client.delete_collection(name="instagram_messages")
                    self.collection = self.client.get_or_create_collection(
                        name="instagram_messages",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self.embedding_function
                    )
                    logger.info("Collection successfully recreated.")
                except Exception as del_err:
                    logger.error(f"Failed to recreate collection: {del_err}")
            else:
                logger.debug(f"ChromaDB collection peek info: {e}")

    def add_messages_batch(self, batch_data, tenant_id: str = "portal"):
        """
        batch_data: list of (chat_name, month, messages_text)
        Respects '---' block boundaries, and splits blocks exceeding 2000 characters
        into overlapping sub-chunks, ensuring each sub-chunk preserves the stable chunk_id.
        """
        all_chunks = []
        all_metadatas = []
        all_ids = []
        seen_ids = set()

        for chat_name, month, messages_text in batch_data:
            # Split into separate message blocks by '---'
            raw_blocks = parse_message_blocks(messages_text)

            for block in raw_blocks:
                # Chunk each block individually to respect boundaries
                sub_chunks = chunk_block_respecting_boundaries(block, max_chars=2000, overlap=200)

                for idx, chunk in enumerate(sub_chunks):
                    # Extract stable chunk_id comment from the block
                    chunk_id_match = _CHUNK_ID_RE.search(chunk)
                    if chunk_id_match:
                        base_id = chunk_id_match.group(1)
                        doc_id = f"{chat_name}_{month}_{base_id}_{idx}"[:100]
                    else:
                        # Legacy fallback: MD5 of content
                        content_hash = hashlib.md5(chunk.encode('utf-8')).hexdigest()
                        doc_id = f"{chat_name}_{month}_{content_hash}_{idx}"[:100]

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
                        "chunk_index": idx,
                        "tenant_id": tenant_id
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

    def add_messages_to_index(self, chat_name, month, messages_text, tenant_id: str = "portal"):
        self.add_messages_batch([(chat_name, month, messages_text)], tenant_id=tenant_id)

    def update_transcribed_message(self, chat_name: str, month: str, old_text: str, new_text: str, tenant_id: str = "portal"):
        """Updates a message chunk in the vector store after transcription."""
        stable_ids = _CHUNK_ID_RE.findall(old_text)

        raw_blocks_old = parse_message_blocks(old_text)
        chunks_old = []
        for block in raw_blocks_old:
            chunks_old.extend(chunk_block_respecting_boundaries(block, max_chars=2000, overlap=200))

        if stable_ids:
            old_ids = [
                f"{chat_name}_{month}_{stable_ids[0]}_{idx}"[:100]
                for idx in range(len(chunks_old))
            ]
        else:
            old_ids = [
                f"{chat_name}_{month}_{hashlib.md5(c.encode('utf-8')).hexdigest()}_{idx}"[:100]
                for idx, c in enumerate(chunks_old)
            ]

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

        self.add_messages_batch([(chat_name, month, new_text)], tenant_id=tenant_id)

    def vacuum_orphaned_vectors(self, tenant_id: str = "portal") -> int:
        """Scans all markdown files and removes ChromaDB vectors with no corresponding disk block."""
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
                    raw_blocks = parse_message_blocks(content)
                    for block in raw_blocks:
                        chunks = chunk_block_respecting_boundaries(block, max_chars=2000, overlap=200)
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
            all_data = self.collection.get(
                where={"tenant_id": tenant_id} if tenant_id else None,
                include=[]
            )
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

    def get_indexed_count(self, chat_name: str, tenant_id: str = "portal") -> int:
        """Retrieves the total count of indexed chunks in ChromaDB for a specific contact."""
        try:
            results = self.collection.get(
                where={"$and": [{"chat_name": chat_name}, {"tenant_id": tenant_id}]},
                include=[]
            )
            return len(results.get("ids", []))
        except Exception as e:
            logger.error(f"Failed to query indexed count for '{chat_name}': {e}")
            return 0

    def get_all_indexed_counts(self, contacts: list[str] | None = None, tenant_id: str = "portal") -> dict:
        """Returns {chat_name: count} for all contacts in ChromaDB."""
        import os

        # Try cache first
        cache_key = f"contacts:index_counts:{tenant_id}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

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
                counts[name] = self.get_indexed_count(name, tenant_id=tenant_id)
                return
            try:
                results = self.collection.get(
                    where={"$and": [{"chat_name": {"$in": batch}}, {"tenant_id": tenant_id}]},
                    include=["metadatas"]
                )
                for meta in results.get("metadatas", []):
                    if meta and "chat_name" in meta:
                        name = meta["chat_name"]
                        if name in counts:
                            counts[name] += 1
            except Exception as e:
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
                        counts[name] = self.get_indexed_count(name, tenant_id=tenant_id)

        batch_size = 20
        for i in range(0, len(contacts), batch_size):
            _count_batch(contacts[i:i + batch_size])

        cache_set(cache_key, counts)
        return counts

    def hybrid_query(self, query: str, chat_name: str, start_month: str | None = None, end_month: str | None = None, tenant_id: str = "portal", n_results: int = 20) -> list[str]:
        """Performs a hybrid search combining dense vector cosine query and sparse keyword BM25 retrieval,
        re-ranked using Reciprocal Rank Fusion (RRF).
        """
        import os

        # 1. Sparse keyword retrieval: load all message blocks for the contact
        raw_blocks = []
        chats_dir = config.CHATS_DIR / chat_name / "Chats"
        if chats_dir.exists():
            md_files = sorted([f for f in os.listdir(chats_dir) if f.endswith(".md")])
            filtered = filter_month_files(md_files, start_month, end_month)
            for f in filtered:
                fpath = chats_dir / f
                try:
                    with open(fpath, encoding="utf-8") as file:
                        content = file.read()
                    blocks = parse_message_blocks(content)
                    raw_blocks.extend(blocks)
                except Exception as e:
                    logger.error(f"Failed to read file {fpath} for BM25: {e}")

        # 2. Run Dense Retrieval in ChromaDB
        dense_chunks = []
        try:
            where_filter = {
                "$and": [
                    {"chat_name": chat_name},
                    {"tenant_id": tenant_id}
                ]
            }
            results = self.collection.query(
                query_texts=[query],
                n_results=50,
                where=where_filter
            )
            if results and results.get('documents') and results['documents'][0]:
                docs = results['documents'][0]
                distances = results['distances'][0] if results.get('distances') else [0.0] * len(docs)
                
                threshold = getattr(config, "RAG_RELEVANCY_THRESHOLD", 0.3)
                for doc, dist in zip(docs, distances):
                    similarity = 1.0 - dist
                    if similarity >= threshold:
                        dense_chunks.append(doc)
        except Exception as e:
            logger.error(f"Dense vector query failed: {e}")

        # 3. If rank-bm25 is installed, run Sparse Retrieval
        sparse_chunks = []
        bm25_available = False
        try:
            from rank_bm25 import BM25Okapi
            bm25_available = True
        except ImportError:
            logger.warning("rank-bm25 is not installed. Sparse search will fall back to simple keyword matching.")
            
        if bm25_available and raw_blocks:
            try:
                tokenized_corpus = [b.lower().split() for b in raw_blocks]
                bm25 = BM25Okapi(tokenized_corpus)
                tokenized_query = query.lower().split()
                
                scores = bm25.get_scores(tokenized_query)
                ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
                
                for idx in ranked_indices:
                    if scores[idx] > 0:
                        sparse_chunks.append(raw_blocks[idx])
                    if len(sparse_chunks) >= 50:
                        break
            except Exception as e:
                logger.error(f"BM25 sparse search failed: {e}")
        elif raw_blocks:
            keywords = [w.lower() for w in query.split() if len(w) > 2]
            scored_blocks = []
            for block in raw_blocks:
                score = sum(1 for kw in keywords if kw in block.lower())
                if score > 0:
                    scored_blocks.append((score, block))
            scored_blocks.sort(key=lambda x: x[0], reverse=True)
            sparse_chunks = [b for s, b in scored_blocks[:50]]

        # 4. Merge results using Reciprocal Rank Fusion (RRF)
        def normalize_chunk(c: str) -> str:
            return " ".join(c.strip().split())

        all_unique_chunks = {}
        for c in dense_chunks + sparse_chunks:
            norm = normalize_chunk(c)
            if norm not in all_unique_chunks:
                all_unique_chunks[norm] = c

        rrf_scores = {}
        k = 60
        
        dense_rank = {normalize_chunk(c): rank for rank, c in enumerate(dense_chunks)}
        sparse_rank = {normalize_chunk(c): rank for rank, c in enumerate(sparse_chunks)}

        for norm, raw_chunk in all_unique_chunks.items():
            score = 0.0
            if norm in dense_rank:
                score += 1.0 / (k + dense_rank[norm])
            if norm in sparse_rank:
                score += 1.0 / (k + sparse_rank[norm])
            rrf_scores[norm] = score

        sorted_norms = sorted(rrf_scores.keys(), key=lambda n: rrf_scores[n], reverse=True)
        final_results = [all_unique_chunks[n] for n in sorted_norms[:n_results]]

        if not final_results and raw_blocks:
            final_results = raw_blocks[-n_results:]

        return final_results



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
