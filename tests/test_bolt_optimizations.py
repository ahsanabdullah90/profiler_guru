import pytest
from src.engine.rag_engine import RAGEngine

def test_rag_engine_add_messages_batch(temp_rag_engine):
    messages = [
        ("Alice", "2024_Q1", "Hello from Alice!"),
        ("Bob", "2024_Q1", "Hi from Bob!"),
    ]

    temp_rag_engine.add_messages_batch(messages)

    results = temp_rag_engine.collection.get()
    assert len(results['documents']) == 2
    assert "Hello from Alice!" in results['documents']
    assert "Hi from Bob!" in results['documents']

def test_rag_engine_stable_ids(temp_rag_engine):
    chat_name = "Charlie"
    quarter = "2024_Q1"
    content = "Stable ID test"

    id1 = temp_rag_engine._generate_id(chat_name, quarter, 0, content)
    id2 = temp_rag_engine._generate_id(chat_name, quarter, 0, content)

    assert id1 == id2
    assert "d41d8cd98f00b204e9800998ecf8427e" not in id1 # empty string md5
    # md5 of "Stable ID test" is e345d515a7eb1eb741d241527dea644b
    assert "e345d515a7eb1eb741d241527dea644b" in id1
