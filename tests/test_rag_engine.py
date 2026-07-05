import pytest
from unittest.mock import MagicMock, patch
from src.engine.rag_engine import RAGEngine

def test_rag_engine_add_messages(temp_rag_engine):
    chat_name = "Alice"
    month = "2023_11"
    messages_text = "### [2023-11-14 10:00:00] Alice\nHello!\n\n---\n### [2023-11-14 10:01:00] Bob\nHi Alice!\n"

    temp_rag_engine.add_messages_to_index(chat_name, month, messages_text)

    results = temp_rag_engine.collection.get()
    assert len(results['documents']) == 2
    docs = results['documents']
    assert any("Hello!" in d for d in docs)
    assert any("Hi Alice!" in d for d in docs)

def test_rag_engine_query_no_results(temp_rag_engine):
    results = temp_rag_engine.collection.query(
        query_texts=["What did Alice say?"],
        n_results=3
    )
    assert results["documents"] is None or len(results["documents"][0]) == 0

def test_rag_engine_query_with_results(temp_rag_engine):
    temp_rag_engine.add_messages_to_index("Alice", "2023_11", "### [2023-11-14] Alice\nPizza is great.")

    results = temp_rag_engine.collection.query(
        query_texts=["What does Alice like?"],
        n_results=1,
        where={"chat_name": "Alice"}
    )
    assert results["documents"] and len(results["documents"][0]) > 0
    assert "pizza" in results["documents"][0][0].lower()

def test_rag_engine_indexed_count(temp_rag_engine):
    assert temp_rag_engine.get_indexed_count("Nonexistent") == 0

    temp_rag_engine.add_messages_to_index("Alice", "2023_11", "### [2023-11-14] Alice\nHello!")
    count = temp_rag_engine.get_indexed_count("Alice")
    assert count >= 1

def test_rag_engine_all_indexed_counts(temp_rag_engine):
    temp_rag_engine.add_messages_to_index("Alice", "2023_11", "### [2023-11-14] Alice\nHello!")
    temp_rag_engine.add_messages_to_index("Bob", "2023_12", "### [2023-12-01] Bob\nHi!")

    with patch('src.engine.rag_engine.cache_get', return_value=None), \
         patch('src.engine.rag_engine.cache_set'):
        counts = temp_rag_engine.get_all_indexed_counts(contacts=["Alice", "Bob", "Empty"])
    assert counts.get("Alice", 0) >= 1
    assert counts.get("Bob", 0) >= 1
    assert counts.get("Empty", 0) == 0

def test_rag_engine_vacuum_orphaned(temp_rag_engine):
    removed = temp_rag_engine.vacuum_orphaned_vectors()
    assert isinstance(removed, int)
