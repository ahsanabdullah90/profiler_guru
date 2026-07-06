"""Tests for user_notes_embedder and inspector note CRUD hooks."""
import os
import json
from pathlib import Path
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from fastapi.testclient import TestClient

from src.utils.config import config
from src.api.api_dependencies import get_current_user, create_jwt_token
from main_api import app


@pytest.fixture(autouse=True)
def _patch_embedding(monkeypatch):
    """Use local embedding model for tests to avoid Ollama dependency."""
    monkeypatch.setattr(config, "EMBEDDING_PROVIDER", "local")
    monkeypatch.setattr(config, "EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    # Also patch get_embedding_function to avoid real model loading entirely
    from chromadb.utils import embedding_functions
    mock_ef = Mock(spec=embedding_functions.EmbeddingFunction)
    mock_ef.__call__ = lambda self, texts: [[0.1 * len(texts)] for _ in texts]
    mock_ef._get_embedding = lambda self, text: [0.1] * 384
    
    # Patch at the module level where it's imported
    monkeypatch.setattr("src.engine.rag_engine.get_embedding_function", lambda provider="local", model_name="", host="", keep_alive=-1: mock_ef)
    monkeypatch.setattr("src.engine.user_notes_embedder.get_embedding_function", lambda provider="local", model_name="", host="", keep_alive=-1: mock_ef)


@pytest.fixture
def temp_inspector_data(tmp_path, monkeypatch):
    """Point inspector store to a temp directory."""
    from src.storage.inspector_store import get_inspector_store
    old_path = config.DATA_DIR
    config.DATA_DIR = tmp_path / "data"
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Reset the singleton
    from src.storage.inspector_store import _inspector_store
    _inspector_store = None

    yield tmp_path

    config.DATA_DIR = old_path


def _auth_headers():
    """Return auth headers for API tests."""
    client = TestClient(app)
    app.dependency_overrides[get_current_user] = lambda: {"sub": "portal"}
    token = create_jwt_token()
    return {"Authorization": f"Bearer {token}"}


def test_chunk_text():
    """Verify the chunking helper splits long text correctly."""
    from src.engine.user_notes_embedder import _chunk_text

    # Short text — should not chunk
    short = "Short note."
    assert _chunk_text(short, chunk_size=1200) == [short]

    # Long text — should chunk
    long_text = "Sentence one. " * 300
    chunks = _chunk_text(long_text, chunk_size=1200, overlap=200)
    assert len(chunks) > 1
    assert "Sentence one." in chunks[0]

    # Empty text
    assert _chunk_text("") == []


@patch("src.engine.user_notes_embedder.chromadb")
def test_embed_and_query(mock_chromadb):
    """Verify embed_note adds and query_notes retrieves."""
    from src.engine.user_notes_embedder import UserNotesEmbedder

    mock_collection = MagicMock()
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_chromadb.PersistentClient.return_value = mock_client

    embedder = UserNotesEmbedder()
    embedder.embed_note("Alice", "note-1", "Test Note", "Alice mentioned she enjoys hiking.", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z")

    # Verify add was called with documents, metadatas, and ids
    mock_collection.add.assert_called_once()
    call_kwargs = mock_collection.add.call_args.kwargs
    assert "documents" in call_kwargs
    assert "metadatas" in call_kwargs
    assert "ids" in call_kwargs
    assert len(call_kwargs["ids"]) >= 1
    assert all("note-1" in id for id in call_kwargs["ids"])

    # Verify the metadata has the correct structure
    meta = call_kwargs["metadatas"][0]
    assert meta["contact_name"] == "Alice"
    assert meta["note_id"] == "note-1"
    assert meta["type"] == "user_note"

    # Test query
    mock_collection.query.return_value = {
        "documents": [["Alice mentioned she enjoys hiking."]],
        "distances": [[0.1]],
        "metadatas": [[meta]]
    }
    results = embedder.query_notes("hiking", "Alice")
    assert len(results) == 1
    assert "hiking" in results[0]


@patch("src.engine.user_notes_embedder.chromadb")
def test_delete_note(mock_chromadb):
    """Verify delete_note removes vectors for the given note_id."""
    from src.engine.user_notes_embedder import UserNotesEmbedder

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": ["note_1_chunk_0"]}
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_chromadb.PersistentClient.return_value = mock_client

    embedder = UserNotesEmbedder()
    embedder.delete_note("note-1")

    mock_collection.get.assert_called_once_with(where={"note_id": "note-1"}, include=[])
    mock_collection.delete.assert_called_once_with(ids=["note_1_chunk_0"])


@patch("src.engine.user_notes_embedder.chromadb")
def test_embed_note_deletes_existing_first(mock_chromadb):
    """Embedding a note should delete old vectors before adding new ones."""
    from src.engine.user_notes_embedder import UserNotesEmbedder

    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": ["note_1_chunk_0"]}
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_collection
    mock_chromadb.PersistentClient.return_value = mock_client

    embedder = UserNotesEmbedder()
    embedder.embed_note("Bob", "note-1", "Title", "Content.", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")

    # Should delete old vectors first
    mock_collection.delete.assert_called_once()
    # Then add new ones
    mock_collection.add.assert_called_once()


def test_note_appears_in_fetch_markdown_snippets(tmp_path, monkeypatch):
    """Notes from inspector_store should be appended to fetch_markdown_snippets output."""
    from src.engine.rag_engine import rag_engine
    from src.storage.inspector_store import get_inspector_store

    monkeypatch.setattr(config, "CHATS_DIR", Path(tmp_path / "chats"))
    monkeypatch.setattr(config, "INSTAGRAM_USERNAME", "Me")

    # Create a minimal markdown file for the contact
    chats_dir = tmp_path / "chats" / "Alice" / "Chats"
    chats_dir.mkdir(parents=True)
    md_file = chats_dir / "2026_07.md"
    md_file.write_text("### [2026-07-01 10:00:00] Alice\nHello!\n\n---\n", encoding="utf-8")

    # Add a note via inspector store
    store = get_inspector_store()
    store.add_note("Alice", "Alice is my friend from college.")

    # Fetch snippets — should include the note
    result = rag_engine.fetch_markdown_snippets("Alice")
    assert "Hello!" in result
    assert "USER OBSERVATIONS" in result
    assert "Alice is my friend" in result


def test_note_absent_when_no_notes(tmp_path, monkeypatch):
    """When no notes exist, fetch_markdown_snippets should not include the notes block."""
    from src.engine.rag_engine import rag_engine

    monkeypatch.setattr(config, "CHATS_DIR", Path(tmp_path / "chats_no_notes"))
    monkeypatch.setattr(config, "INSTAGRAM_USERNAME", "Me")

    chats_dir = tmp_path / "chats_no_notes" / "Bob" / "Chats"
    chats_dir.mkdir(parents=True)
    md_file = chats_dir / "2026_07.md"
    md_file.write_text("### [2026-07-01 10:00:00] Bob\nHi!\n\n---\n", encoding="utf-8")

    result = rag_engine.fetch_markdown_snippets("Bob")
    assert "Hi!" in result
    assert "USER OBSERVATIONS" not in result
