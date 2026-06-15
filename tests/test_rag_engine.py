import pytest
from unittest.mock import MagicMock, patch
from src.engine.rag_engine import RAGEngine

def test_rag_engine_add_messages(temp_rag_engine):
    chat_name = "Alice"
    quarter = "2023_Q4"
    messages_text = "### [2023-11-14 10:00:00] Alice\nHello!\n\n---\n### [2023-11-14 10:01:00] Bob\nHi Alice!\n"

    temp_rag_engine.add_messages_to_index(chat_name, quarter, messages_text)

    # Check if messages were added to the collection
    results = temp_rag_engine.collection.get()
    assert len(results['documents']) >= 2
    assert any("Hello!" in doc for doc in results['documents'])
    assert any("Hi Alice!" in doc for doc in results['documents'])

def test_rag_engine_query_no_results(temp_rag_engine):
    # Mock model to avoid configuration error if key is missing
    temp_rag_engine.model = MagicMock()

    # Query an empty index
    response = temp_rag_engine.query("What did Alice say?")
    assert response == "No relevant chat history found for this query."

def test_rag_engine_analyze_profile_no_results(temp_rag_engine):
    # Mock model
    temp_rag_engine.model = MagicMock()

    response = temp_rag_engine.analyze_profile("Alice")
    assert response == "No messages found for Alice in the index."

def test_rag_engine_query_with_results(temp_rag_engine):
    # Add data
    temp_rag_engine.add_messages_to_index("Alice", "2023_Q4", "### [2023-11-14] Alice\nPizza is great.")

    # Mock model
    mock_response = MagicMock()
    mock_response.text = "The user likes pizza."
    temp_rag_engine.model = MagicMock()
    temp_rag_engine.model.generate_content.return_value = mock_response

    response = temp_rag_engine.query("What does Alice like?")
    assert "pizza" in response.lower()
    temp_rag_engine.model.generate_content.assert_called_once()

def test_rag_engine_query_filters(temp_rag_engine, mocker):
    # Mock model and collection query
    temp_rag_engine.model = MagicMock()
    mock_query = mocker.patch.object(temp_rag_engine.collection, 'query')
    mock_query.return_value = {'documents': [[]]} # Simulate no results to focus on call args

    # Case 1: No chat filter
    temp_rag_engine.query("Hello")
    mock_query.assert_called_with(
        query_texts=["Hello"],
        n_results=10,
        where=None
    )

    # Case 2: With chat filter
    temp_rag_engine.query("Hello", chat_filter="Alice")
    mock_query.assert_called_with(
        query_texts=["Hello"],
        n_results=10,
        where={"chat_name": "Alice"}
    )
