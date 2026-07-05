# tests/test_knowledge_api.py
import os
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from src.utils.config import config
from src.api.api_dependencies import get_current_user, create_jwt_token
from src.engine.metrics_engine import MetricsEngine
from main_api import app

@pytest.fixture
def temp_knowledge_dir(tmp_path):
    """Fixture to point knowledge base storage to a temp directory."""
    old_data_dir = config.DATA_DIR
    
    temp_dir = tmp_path / "data"
    temp_dir.mkdir(parents=True, exist_ok=True)
    config.DATA_DIR = temp_dir
    
    # Re-initialize MetricsEngine singleton with temp path
    MetricsEngine._instance = None
    metrics = MetricsEngine(db_path=temp_dir / "psych_profiles.db")
    
    yield temp_dir
    
    config.DATA_DIR = old_data_dir
    MetricsEngine._instance = None

def test_knowledge_lifecycle(temp_knowledge_dir):
    # Overwrite auth dependencies
    app.dependency_overrides[get_current_user] = lambda: {"sub": "portal"}
    
    client = TestClient(app)
    token = create_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # 1. List documents (should be empty)
        res = client.get("/api/v1/knowledge", headers=headers)
        assert res.status_code == 200
        assert len(res.json()["documents"]) == 0
        
        # 2. Upload a text document
        # We write a mock text file
        dummy_file = temp_knowledge_dir / "test_attachment.txt"
        with open(dummy_file, "w", encoding="utf-8") as f:
            f.write("Attachment styles determine how individuals react in relationships. "
                    "Secure attachment leads to trusting partnerships. "
                    "Avoidant attachment style triggers distance-seeking behavior.")
                    
        with open(dummy_file, "rb") as f:
            upload_res = client.post(
                "/api/v1/knowledge",
                headers=headers,
                data={
                    "title": "Attachment Styles Overview",
                    "author": "Mary Ainsworth",
                    "year": 1978
                },
                files={"file": ("test_attachment.txt", f, "text/plain")}
            )
            
        print("DEBUG UPLOAD STATUS:", upload_res.status_code)
        print("DEBUG UPLOAD TEXT:", upload_res.text)
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "queued"
        doc_id = upload_res.json()["document_id"]
        assert doc_id is not None
        
        # The background task is run synchronously by TestClient
        saved_file = Path(config.DATA_DIR) / "knowledge_files" / f"{doc_id}_test_attachment.txt"
        assert saved_file.exists()
        
        # 3. List documents again (should show completed)
        res_list = client.get("/api/v1/knowledge", headers=headers)
        assert res_list.status_code == 200
        docs = res_list.json()["documents"]
        assert len(docs) == 1
        assert docs[0]["document_id"] == doc_id
        assert docs[0]["embedding_status"] == "completed"
        assert docs[0]["author"] == "Mary Ainsworth"
        assert docs[0]["year"] == 1978
        
        # 4. Query the knowledge base (positive match)
        # Mock LLM dispatch response
        with patch('src.api.api_knowledge.llm_dispatcher.dispatch') as mock_dispatch:
            mock_dispatch.return_value = "Secure attachment style leads to trusting relationships [Source 1]."
            
            query_res = client.post(
                "/api/v1/knowledge/query",
                headers=headers,
                json={"query": "What does secure attachment style lead to?"}
            )
            
            assert query_res.status_code == 200
            assert "Secure attachment" in query_res.json()["response"]
            assert len(query_res.json()["citations"]) == 1
            assert query_res.json()["citations"][0]["title"] == "Attachment Styles Overview"
            
        # 5. Query with no matching context (should return generic fallback politely)
        query_empty = client.post(
            "/api/v1/knowledge/query",
            headers=headers,
            json={"query": "What is the capital of France?"}
        )
        assert query_empty.status_code == 200
        assert "information is not available" in query_empty.json()["response"]
        assert len(query_empty.json()["citations"]) == 0
        
        # 6. Delete document
        del_res = client.delete(f"/api/v1/knowledge/{doc_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "success"
        
        # Verify it's gone from list
        res_final = client.get("/api/v1/knowledge", headers=headers)
        assert len(res_final.json()["documents"]) == 0
        
    finally:
        app.dependency_overrides.clear()
