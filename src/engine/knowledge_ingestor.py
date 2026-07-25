# src/engine/knowledge_ingestor.py
import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
import chromadb
from chromadb.utils import embedding_functions

from src.utils.config import config
from src.utils.logger import logger
from src.engine.metrics_engine import MetricsEngine

# Use the configured embedding function (ollama + bge-m3 by default)
import threading
import re
from src.engine.rag_engine import get_embedding_function

_INGEST_LOCK = threading.Semaphore(1)

_HEADING_RE = re.compile(
    r'^(?:Chapter|Section|Part|Appendix|Unit)\s+\d+|' # e.g. Chapter 4
    r'^\d+(?:\.\d+)+\s+[A-Za-z]|'                     # e.g. 1.2.3 Attachment Style
    r'^[A-Z][A-Z\s\-\&\,]{3,50}$'                      # Short all-caps string
)

def _detect_headings(lines: list[str]) -> set[str]:
    headings = set()
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING_RE.match(stripped):
            if len(stripped) < 70:
                headings.add(stripped)
    return headings

class KnowledgeIngestor:
    def __init__(self):
        # We share the same persistent storage parent folder to centralize assets, but use a new DB path or collection.
        # To avoid file lock contention with the main RAG client, we open a collection inside chroma_db or in a separate folder.
        # Placing it in config.DATA_DIR / "chroma_db" allows sharing a single client, or using a dedicated client folder.
        # Let's use a dedicated folder "chroma_knowledge" to keep psychology documents separate and completely decoupled.
        self.db_path = str(config.DATA_DIR / "chroma_knowledge")
        os.makedirs(self.db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.db_path)
        
        self.embedding_function = get_embedding_function(
            provider=config.EMBEDDING_PROVIDER,
            model_name=config.EMBEDDING_MODEL,
            host=config.OLLAMA_HOST
        )
        
        self.collection = self.client.get_or_create_collection(
            name="psychology_kb",
            metadata={"hnsw:space": "cosine"},
            embedding_function=self.embedding_function
        )
        self.metrics_engine = MetricsEngine()
        self._validate_embedding_dimension()
        
        # Ensure raw file storage folder exists
        self.storage_dir = Path(config.DATA_DIR) / "knowledge_files"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _validate_embedding_dimension(self):
        """Validates that the existing psychology_kb collection dimension matches the configured model."""
        try:
            self.collection.peek(limit=1)
        except Exception as e:
            if "dimension" in str(e).lower() or "mismatch" in str(e).lower():
                logger.warning("ChromaDB knowledge collection dimension mismatch. Recreating...")
                try:
                    self.client.delete_collection(name="psychology_kb")
                    self.collection = self.client.get_or_create_collection(
                        name="psychology_kb",
                        metadata={"hnsw:space": "cosine"},
                        embedding_function=self.embedding_function
                    )
                    # Mark all existing documents as needs_reindexing in SQLite
                    self.metrics_engine.mark_all_knowledge_documents_for_reindexing()
                    # Trigger resumption of indexing tasks in a background thread
                    import threading
                    t = threading.Thread(target=self.resume_indexing_tasks, daemon=True)
                    t.start()
                except Exception as del_err:
                    logger.error(f"Failed to recreate knowledge collection: {del_err}")

    def extract_pages(self, filepath: Path) -> list[tuple[int, str]]:
        """Extracts plain text from PDF, TXT, or Markdown documents page-by-page."""
        suffix = filepath.suffix.lower()
        if suffix == ".pdf":
            import pdfplumber
            pages = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split("\n")
                        # Detect headings on this page before stripping lines
                        heading_lines = _detect_headings(lines)
                        # Strip lines <= 10 chars unless they are detected headings
                        cleaned = [l for l in lines if len(l.strip()) > 10 or l.strip() in heading_lines]
                        pages.append((page.page_number, "\n".join(cleaned)))
                    else:
                        pages.append((page.page_number, ""))
            return pages
        elif suffix in [".txt", ".md", ".markdown"]:
            with open(filepath, encoding="utf-8") as f:
                # Page number is 0 for unstructured text/markdown files
                return [(0, f.read())]
        elif suffix == ".docx":
            import docx
            doc = docx.Document(filepath)
            pages = []
            current_page_text = []
            current_len = 0
            page_num = 1
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                current_page_text.append(text)
                current_len += len(text)
                if current_len >= 2500:
                    pages.append((page_num, "\n".join(current_page_text)))
                    current_page_text = []
                    current_len = 0
                    page_num += 1
            if current_page_text:
                pages.append((page_num, "\n".join(current_page_text)))
            return pages
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def chunk_text(self, text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
        """Splits raw text into sentence-aware overlapping chunks."""
        import re
        # Sentence separation heuristic
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence)
            if current_length + sentence_len > chunk_size:
                chunks.append(" ".join(current_chunk))
                # Form overlap from trailing sentences
                overlap_chunk = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) < overlap:
                        overlap_chunk.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_chunk = overlap_chunk
                current_length = overlap_len
                
            current_chunk.append(sentence)
            current_length += sentence_len
            
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        return chunks

    def process_and_ingest(self, source_path: Path, title: str, author: str | None = None, year: int | None = None, original_filename: str = "") -> str:
        """Copies the original file, extracts text page-by-page, chunks it, uploads to ChromaDB, and indexes in SQLite."""
        filename = original_filename if original_filename else source_path.name
        
        # 1. Generate unique document ID based on file content hash
        hasher = hashlib.sha256()
        with open(source_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        doc_id = hasher.hexdigest()[:16] # Shortened SHA256
        
        # 2. Preserve original file in database storage path
        saved_path = self.storage_dir / f"{doc_id}_{filename}"
        if not saved_path.exists():
            shutil.copy2(source_path, saved_path)
        
        # 3. Add initial record to SQLite connection manager (skipped if pre-registered)
        # We use default status of "indexing"
        self.metrics_engine.add_knowledge_document(
            doc_id=doc_id,
            filename=filename,
            filepath=str(saved_path),
            title=title,
            author=author,
            year=year,
            status="indexing",
            total_pages=0,
            processed_pages=0
        )
        
        # 4. Process and embed text under the module-level lock
        try:
            with _INGEST_LOCK:
                pages = self.extract_pages(saved_path)
                total_pages = len(pages)
                if total_pages == 0:
                    raise ValueError("Document appears to be empty or unreadable.")
                
                empty_pages = sum(1 for page_num, page_text in pages if not page_text.strip())
                if empty_pages / total_pages >= 0.80:
                    raise ValueError("Scanned or image-only PDF detected. Text extraction returned no content. Please upload a text-based PDF.")

                self.metrics_engine.update_knowledge_document_progress(doc_id, 0, total_pages, "indexing")
                
                # Concatenate all page texts and track offsets
                concatenated_text = ""
                page_offsets = [] # list of (start_offset, end_offset, page_num)
                heading_offsets = [] # list of (offset, heading_text)
                
                for page_num, page_text in pages:
                    start_off = len(concatenated_text)
                    
                    # Scan for headings on this page
                    lines = page_text.split("\n")
                    for l in lines:
                        stripped_l = l.strip()
                        if _HEADING_RE.match(stripped_l) and len(stripped_l) < 70:
                            line_idx = page_text.find(stripped_l)
                            if line_idx != -1:
                                heading_offsets.append((start_off + line_idx, stripped_l))
                                
                    concatenated_text += page_text + "\n\n"
                    end_off = len(concatenated_text)
                    page_offsets.append((start_off, end_off, page_num))
                
                # Chunk the concatenated text continuously
                chunks = self.chunk_text(concatenated_text)
                
                all_ids = []
                all_docs = []
                all_metas = []
                global_chunk_idx = 0
                search_pos = 0
                
                for chunk in chunks:
                    # Locate chunk position in concatenated_text to assign page and heading
                    chunk_idx = concatenated_text.find(chunk, search_pos)
                    if chunk_idx != -1:
                        search_pos = chunk_idx + len(chunk)
                    else:
                        chunk_idx = concatenated_text.find(chunk) # fallback
                    
                    # Determine page number
                    page_num = 0
                    if chunk_idx != -1:
                        for start_off, end_off, p_num in page_offsets:
                            if start_off <= chunk_idx < end_off:
                                page_num = p_num
                                break
                    
                    # Determine active heading
                    active_heading = ""
                    if chunk_idx != -1:
                        for h_off, h_text in heading_offsets:
                            if h_off <= chunk_idx:
                                active_heading = h_text
                            else:
                                break
                    
                    prefixed_chunk = f"[{active_heading}] {chunk}" if active_heading else chunk
                    
                    chunk_meta = {
                        "document_id": doc_id,
                        "chunk_index": global_chunk_idx,
                        "title": title,
                        "author": author or "Unknown",
                        "year": year or 0
                    }
                    if page_num > 0:
                        chunk_meta["page_number"] = page_num
                        
                    all_ids.append(f"{doc_id}_chunk_{global_chunk_idx}")
                    all_docs.append(prefixed_chunk)
                    all_metas.append(chunk_meta)
                    global_chunk_idx += 1
                    
                    # Batch write into ChromaDB every 50 chunks to keep memory usage flat
                    if len(all_ids) >= 50:
                        self.collection.add(
                            ids=all_ids,
                            documents=all_docs,
                            metadatas=all_metas
                        )
                        all_ids, all_docs, all_metas = [], [], []
                        # Update progress based on the current chunk's page number
                        self.metrics_engine.update_knowledge_document_progress(doc_id, page_num, total_pages, "indexing")
                
                # Flush remaining chunks
                if all_ids:
                    self.collection.add(
                        ids=all_ids,
                        documents=all_docs,
                        metadatas=all_metas
                    )
                
                # Update status to completed
                self.metrics_engine.update_knowledge_document_progress(doc_id, total_pages, total_pages, "completed")
                logger.info(f"Ingested document {title} successfully. Total chunks: {global_chunk_idx}")
                return doc_id
        except Exception as e:
            logger.error(f"Failed to ingest knowledge document {title}: {e}")
            self.metrics_engine.update_embedding_status(doc_id, "failed")
            # Cleanup saved file on complete failures
            if saved_path.exists():
                try:
                    os.unlink(saved_path)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to cleanup saved file {saved_path}: {cleanup_err}")
            raise e

    def resume_indexing_tasks(self):
        """Restart ingestion for documents interrupted mid-indexing."""
        interrupted = self.metrics_engine.get_interrupted_knowledge_documents()
        for doc in interrupted:
            doc_id = doc["document_id"]
            saved_path = Path(doc["filepath"])
            if not saved_path.exists():
                logger.warning(f"Resume: Saved file missing for document {doc_id}, marking failed.")
                self.metrics_engine.update_embedding_status(doc_id, "failed")
                continue
            
            # Wipe partial vectors to avoid duplicates
            try:
                self.collection.delete(where={"document_id": doc_id})
                logger.info(f"Resume: Wiped partial vectors for document {doc_id}.")
            except Exception as e:
                logger.warning(f"Resume: Failed to delete partial vectors for {doc_id}: {e}")
            
            # Re-queue background thread to run the ingestion from scratch
            import threading
            t = threading.Thread(
                target=self.process_and_ingest,
                args=(saved_path, doc["title"], doc["author"], doc["year"]),
                kwargs={"original_filename": doc["filename"]},
                daemon=True
            )
            t.start()
            logger.info(f"Resume: Spawned ingestion worker thread for '{doc['title']}' ({doc_id})")

    def hybrid_search(self, query: str, n_results: int = 6) -> list[dict]:
        """Performs a hybrid search combining dense vector cosine query and sparse keyword BM25 retrieval,
        re-ranked using Reciprocal Rank Fusion (RRF).
        """
        # 1. Dense retrieval
        dense_results = []
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=50
            )
            if results and results.get('documents') and results['documents'][0]:
                docs = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                threshold = getattr(config, "RAG_RELEVANCY_THRESHOLD", 0.3)
                for doc, meta, dist in zip(docs, metadatas, distances):
                    similarity = 1.0 - dist
                    if similarity >= threshold:
                        dense_results.append({
                            "text": doc,
                            "metadata": meta,
                            "similarity": similarity
                        })
        except Exception as e:
            logger.error(f"KB dense query failed: {e}")

        # 2. Sparse retrieval
        sparse_results = []
        try:
            # Get all documents in the collection
            all_data = self.collection.get(include=['documents', 'metadatas'])
            if all_data and all_data.get('documents'):
                all_docs = all_data['documents']
                all_metas = all_data['metadatas']
                
                from rank_bm25 import BM25Okapi
                tokenized_corpus = [doc.lower().split() for doc in all_docs]
                bm25 = BM25Okapi(tokenized_corpus)
                tokenized_query = query.lower().split()
                
                scores = bm25.get_scores(tokenized_query)
                ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
                
                for idx in ranked_indices:
                    if scores[idx] > 0.0:
                        sparse_results.append({
                            "text": all_docs[idx],
                            "metadata": all_metas[idx],
                            "score": scores[idx]
                        })
                    if len(sparse_results) >= 50:
                        break
        except Exception as e:
            logger.error(f"KB sparse query failed: {e}")

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_scores = {}
        k = 60
        
        # Dense rank scoring
        for rank, item in enumerate(dense_results):
            key = f"{item['metadata']['document_id']}_{item['metadata']['chunk_index']}"
            rrf_scores[key] = {
                "item": item,
                "score": 1.0 / (k + rank)
            }
            
        # Sparse rank scoring
        for rank, item in enumerate(sparse_results):
            key = f"{item['metadata']['document_id']}_{item['metadata']['chunk_index']}"
            if key in rrf_scores:
                rrf_scores[key]["score"] += 1.0 / (k + rank)
            else:
                rrf_scores[key] = {
                    "item": {
                        "text": item["text"],
                        "metadata": item["metadata"],
                        "similarity": 0.40  # Approximate relevance for sparse-only matches
                    },
                    "score": 1.0 / (k + rank)
                }
                
        # Sort by RRF score descending
        fused = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
        
        # Format output
        results_list = []
        for f in fused[:n_results]:
            results_list.append(f["item"])
            
        return results_list

    def remove_document(self, doc_id: str):
        """Wipes matching vectors, original files, and SQLite records for a document."""
        # 1. Fetch document filepath from SQLite
        all_docs = self.metrics_engine.get_all_knowledge_documents()
        matched_doc = next((d for d in all_docs if d["document_id"] == doc_id), None)
        
        if not matched_doc:
            raise ValueError(f"Document ID {doc_id} not found in database registry.")
            
        # 2. Delete embeddings from ChromaDB
        try:
            self.collection.delete(where={"document_id": doc_id})
        except Exception as e:
            logger.error(f"Failed to delete embeddings from ChromaDB for {doc_id}: {e}")
            
        # 3. Delete raw preserved file
        filepath = Path(matched_doc["filepath"])
        if filepath.exists():
            try:
                os.unlink(filepath)
            except Exception as e:
                logger.error(f"Failed to delete raw file {filepath}: {e}")
                
        # 4. Remove from SQLite records
        self.metrics_engine.delete_knowledge_document(doc_id)
        logger.info(f"Successfully removed document {doc_id} from knowledge base.")


from src.utils.lazy_proxy import LazyProxy

knowledge_ingestor = LazyProxy(KnowledgeIngestor)
