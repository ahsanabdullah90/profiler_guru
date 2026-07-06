"""Embed user notes into a dedicated ChromaDB collection for RAG search.

Notes are stored in a separate `user_notes` collection alongside the
existing `instagram_messages` and `psychology_kb` collections.
This allows notes to appear in RAG chat queries, global search,
and assessment prompts via vector search.
"""
import os
import chromadb
from chromadb.utils import embedding_functions

from src.utils.config import config
from src.utils.logger import logger
from src.engine.rag_engine import get_embedding_function


def _chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks at sentence boundaries."""
    import re
    if not text or not text.strip():
        return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)
        if current_length + sentence_len > chunk_size:
            chunks.append(" ".join(current_chunk))
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

    if text.strip():
        chunks.append(" ".join(current_chunk))
    return chunks


class UserNotesEmbedder:
    """Manages user note vectors in a dedicated ChromaDB collection."""

    def __init__(self):
        self._collection = None

    def _get_collection(self):
        """Lazy-init the ChromaDB collection."""
        if self._collection is not None:
            return self._collection

        db_path = str(config.DATA_DIR / "chroma_user_notes")
        os.makedirs(db_path, exist_ok=True)
        client = chromadb.PersistentClient(path=db_path)
        ef = get_embedding_function(
            provider=config.EMBEDDING_PROVIDER,
            model_name=config.EMBEDDING_MODEL,
            host=config.OLLAMA_HOST
        )
        self._collection = client.get_or_create_collection(
            name="user_notes",
            metadata={"hnsw:space": "cosine"},
            embedding_function=ef
        )
        return self._collection

    def embed_note(self, contact_name: str, note_id: str, title: str, content: str,
                   created_at: str, updated_at: str):
        """Embed a note into the user_notes collection.
        Deletes any existing vectors for the same note_id first, then
        chunks and adds the new content.
        """
        self.delete_note(note_id)
        coll = self._get_collection()

        full_text = f"{title}\n\n{content}" if title else content
        chunks = _chunk_text(full_text, chunk_size=1200, overlap=200)

        documents = []
        metadatas = []
        ids = []

        for idx, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "contact_name": contact_name,
                "note_id": note_id,
                "type": "user_note",
                "created_at": created_at,
                "updated_at": updated_at,
                "chunk_index": idx,
                "chunk_total": len(chunks),
            })
            ids.append(f"note_{note_id}_chunk_{idx}")

        if documents:
            coll.add(documents=documents, metadatas=metadatas, ids=ids)
            logger.info(f"Embedded note {note_id} for {contact_name} ({len(chunks)} chunks)")

    def delete_note(self, note_id: str):
        """Remove all vectors for a given note_id."""
        coll = self._get_collection()
        try:
            # Fetch all IDs matching this note_id
            existing = coll.get(where={"note_id": note_id}, include=[])
            ids_to_delete = existing.get("ids", [])
            if ids_to_delete:
                coll.delete(ids=ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} vectors for note {note_id}")
        except Exception as e:
            logger.warning(f"Failed to delete vectors for note {note_id}: {e}")

    def query_notes(self, query: str, contact_name: str, n_results: int = 50) -> list[str]:
        """Vector search on user_notes for a specific contact.
        Returns a list of document strings ordered by relevance.
        """
        coll = self._get_collection()
        try:
            results = coll.query(
                query_texts=[query],
                n_results=n_results,
                where={"contact_name": contact_name}
            )
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                distances = results.get("distances", [None])[0] or [0.0] * len(docs)
                threshold = getattr(config, "RAG_RELEVANCY_THRESHOLD", 0.3)
                return [
                    doc for doc, dist in zip(docs, distances)
                    if 1.0 - dist >= threshold
                ]
        except Exception as e:
            logger.warning(f"User notes query failed for {contact_name}: {e}")
        return []

    def get_notes_for_contact(self, contact_name: str) -> list[dict]:
        """Return all note chunks for a contact as dicts with document + metadata."""
        coll = self._get_collection()
        try:
            results = coll.get(where={"contact_name": contact_name, "chunk_index": 0}, include=["metadatas"])
            metas = results.get("metadatas", [])
            # Deduplicate by note_id (only chunk_index 0 gives us one entry per note)
            seen = set()
            notes = []
            for m in metas:
                if m and m.get("note_id") not in seen:
                    seen.add(m["note_id"])
                    notes.append(m)
            return notes
        except Exception as e:
            logger.warning(f"Failed to get notes for {contact_name}: {e}")
        return []

    def get_note_count(self, contact_name: str) -> int:
        """Return count of distinct notes for a contact."""
        return len(self.get_notes_for_contact(contact_name))


user_notes_embedder = UserNotesEmbedder()