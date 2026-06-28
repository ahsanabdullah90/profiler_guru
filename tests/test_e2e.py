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

    # Verify the message was indexed in ChromaDB
    results = temp_rag_engine.collection.query(
        query_texts=["coffee"],
        n_results=1,
        where={"chat_name": "Bob"}
    )
    assert results["documents"] and len(results["documents"][0]) > 0
    assert "coffee" in results["documents"][0][0].lower()

