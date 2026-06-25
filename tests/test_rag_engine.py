import pytest
from unittest.mock import MagicMock, patch
from src.engine.rag_engine import RAGEngine

def test_rag_engine_add_messages(temp_rag_engine):
    chat_name = "Alice"
    month = "2023_11"
    messages_text = "### [2023-11-14 10:00:00] Alice\nHello!\n\n---\n### [2023-11-14 10:01:00] Bob\nHi Alice!\n"

    temp_rag_engine.add_messages_to_index(chat_name, month, messages_text)

    # Check if messages were added as a single combined context chunk
    results = temp_rag_engine.collection.get()
    assert len(results['documents']) == 1
    doc = results['documents'][0]
    assert "Hello!" in doc
    assert "Hi Alice!" in doc

def test_rag_engine_query_no_results(temp_rag_engine):
    # Mock model to avoid configuration error if key is missing
    temp_rag_engine.model = MagicMock()

    # Query an empty index
    response = temp_rag_engine.query("What did Alice say?", user_consent=True)
    assert response == "No relevant chat history found for this query."

def test_rag_engine_analyze_profile_no_results(temp_rag_engine):
    # Mock model
    temp_rag_engine.model = MagicMock()

    response = temp_rag_engine.analyze_profile("Alice", user_consent=True)
    assert response == "No messages found for 'Alice' in the index."


def test_rag_engine_query_with_results(temp_rag_engine):
    # Add data
    temp_rag_engine.add_messages_to_index("Alice", "2023_11", "### [2023-11-14] Alice\nPizza is great.")

    # Mock model
    mock_response = MagicMock()
    mock_response.text = "The user likes pizza."
    temp_rag_engine.model = MagicMock()
    temp_rag_engine.model.generate_content.return_value = mock_response

    response = temp_rag_engine.query("What does Alice like?", user_consent=True)
    assert "pizza" in response.lower()
    temp_rag_engine.model.generate_content.assert_called_once()

def test_rag_engine_query_ollama_fallback(temp_rag_engine):
    # Add data
    temp_rag_engine.add_messages_to_index("Alice", "2023_11", "### [2023-11-14] Alice\nPizza is great.")

    # With user_consent=False (or provider="ollama"), it should fall back to Ollama
    with patch('src.engine.rag_engine.ollama_client') as mock_ollama:
        mock_ollama.generate.return_value = "Ollama response: likes pizza"
        
        response = temp_rag_engine.query("What does Alice like?", provider="ollama")
        assert "ollama" in response.lower()
        mock_ollama.generate.assert_called_once()

