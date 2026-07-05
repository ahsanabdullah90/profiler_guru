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

# Re-use the default local embedding function (all-MiniLM-L6-v2, dimension 384)
from src.engine.rag_engine import get_embedding_function

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
        
        self._validate_embedding_dimension()
        self.metrics_engine = MetricsEngine()
        
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
                except Exception as del_err:
                    logger.error(f"Failed to recreate knowledge collection: {del_err}")

    def extract_text(self, filepath: Path) -> str:
        """Extracts plain text from PDF, TXT, or Markdown documents."""
        suffix = filepath.suffix.lower()
        if suffix == ".pdf":
            import pdfplumber
            text_blocks = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # Strip standard header/footer boilerplate (e.g. page numbers)
                        lines = text.split("\n")
                        cleaned = [l for l in lines if len(l.strip()) > 10]
                        text_blocks.append("\n".join(cleaned))
            return "\n\n".join(text_blocks)
        elif suffix in [".txt", ".md", ".markdown"]:
            with open(filepath, encoding="utf-8") as f:
                return f.read()
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
        """Copies the original file, extracts text, chunks it, uploads to ChromaDB, and indexes in SQLite."""
        filename = original_filename if original_filename else source_path.name
        
        # 1. Generate unique document ID based on file content hash
        hasher = hashlib.sha256()
        with open(source_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        doc_id = hasher.hexdigest()[:16] # Shortened SHA256
        
        # 2. Preserve original file in database storage path
        saved_path = self.storage_dir / f"{doc_id}_{filename}"
        shutil.copy2(source_path, saved_path)
        
        # 3. Add initial record to SQLite connection manager
        self.metrics_engine.add_knowledge_document(
            doc_id=doc_id,
            filename=filename,
            filepath=str(saved_path),
            title=title,
            author=author,
            year=year,
            status="indexing"
        )
        
        # 4. Process and embed text in background/synchronous task
        try:
            raw_text = self.extract_text(saved_path)
            chunks = self.chunk_text(raw_text)
            
            if not chunks:
                raise ValueError("Extracted document contains no valid readable text.")
                
            ids = []
            documents = []
            metadatas = []
            
            for idx, c in enumerate(chunks):
                ids.append(f"{doc_id}_chunk_{idx}")
                documents.append(c)
                metadatas.append({
                    "document_id": doc_id,
                    "chunk_index": idx,
                    "title": title,
                    "author": author or "Unknown",
                    "year": year or 0
                })
                
            # Batch load into ChromaDB
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            self.metrics_engine.update_embedding_status(doc_id, "completed")
            logger.info(f"Ingested document {title} successfully. Chunks: {len(chunks)}")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to ingest knowledge document {title}: {e}")
            self.metrics_engine.update_embedding_status(doc_id, "failed")
            # Cleanup saved file on complete failures
            if saved_path.exists():
                try:
                    os.unlink(saved_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup saved file {saved_path}: {e}")
            # Propagate error
            raise e

    def remove_document(self, doc_id: str):
        """Wipes matching vectors, original files, and SQLite records for a document."""
        # 1. Fetch document filepath from SQLite
        all_docs = self.metrics_engine.get_all_knowledge_documents()
        matched_doc = next((d for d in all_docs if d["document_id"] == doc_id), None)
        
        if not matched_doc:
            raise ValueError(f"Document ID {doc_id} not found in database registry.")
            
        # 2. Delete embeddings from ChromaDB
        # ChromaDB allows deleting by metadata matches
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
