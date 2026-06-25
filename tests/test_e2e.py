import os
import json
import pytest
from unittest.mock import MagicMock, patch
from src.engine.data_importer import InstagramDataImporter
from src.engine.rag_engine import rag_engine

def test_end_to_end_flow(tmp_path, temp_storage, temp_rag_engine):
    # Use the temp_rag_engine instead of the singleton for isolation
    # We will patch the rag_engine singleton in data_importer

    # Setup mock Instagram export structure
    export_path = tmp_path / "instagram_export"
    messages_path = export_path / "messages" / "inbox" / "bob_456"
    messages_path.mkdir(parents=True)

    message_data = {
        "title": "Bob",
        "messages": [
            {
                "sender_name": "Bob",
                "timestamp_ms": 1700000000000,
                "content": "Do you want to grab coffee?"
            }
        ]
    }

    with open(messages_path / "message_1.json", "w", encoding='utf-8') as f:
        json.dump(message_data, f)

    # Patch the global rag_engine used in importer
    with patch('src.engine.data_importer.rag_engine', temp_rag_engine):
        importer = InstagramDataImporter(temp_storage)
        importer.import_from_json(str(export_path))

    # Verify it's in RAG
    # We need to mock the Gemini model for the query
    mock_response = MagicMock()
    mock_response.text = "Bob asked about coffee."
    temp_rag_engine.gemini_client = MagicMock()
    temp_rag_engine.gemini_client.models.generate_content.return_value = mock_response

    response = temp_rag_engine.query("What did Bob ask?", user_consent=True)
    assert "coffee" in response.lower()

