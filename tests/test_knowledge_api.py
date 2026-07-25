# tests/test_knowledge_api.py
import os
import time
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
            
        assert upload_res.status_code == 200
        assert upload_res.json()["status"] == "queued"
        doc_id = upload_res.json()["document_id"]
        assert doc_id is not None
        
        # 3. Poll for background task completion (TestClient runs background tasks async)
        max_wait = 30  # seconds
        poll_interval = 0.5
        elapsed = 0
        docs = []
        while elapsed < max_wait:
            res_list = client.get("/api/v1/knowledge", headers=headers)
            docs = res_list.json()["documents"]
            if docs and docs[0].get("embedding_status") == "completed":
                break
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        # Verify document was ingested
        assert len(docs) == 1
        assert docs[0]["document_id"] == doc_id
        assert docs[0]["embedding_status"] == "completed"
        assert docs[0]["author"] == "Mary Ainsworth"
        assert docs[0]["year"] == 1978
        
        # Verify saved file exists
        saved_file = Path(config.DATA_DIR) / "knowledge_files" / f"{doc_id}_test_attachment.txt"
        assert saved_file.exists(), f"Saved file not found at {saved_file}"
        
        # 4. Query the knowledge base (mock ChromaDB + LLM to avoid similarity threshold issues)
        mock_ingestor = MagicMock()
        mock_ingestor.hybrid_search.return_value = [
            {
                "text": "Attachment styles determine how individuals react in relationships.",
                "metadata": {"document_id": doc_id, "chunk_index": 0, "title": "Attachment Styles Overview", "author": "Mary Ainsworth", "year": 1978},
                "similarity": 0.90
            }
        ]
        with patch('src.api.api_knowledge.KnowledgeIngestor', return_value=mock_ingestor), \
             patch('src.api.api_knowledge.llm_dispatcher') as mock_llm:
            mock_llm.dispatch.return_value = "Secure attachment style leads to trusting relationships [1]."
            
            query_res = client.post(
                "/api/v1/knowledge/query",
                headers=headers,
                json={"query": "What does secure attachment style lead to?"}
            )
            
            assert query_res.status_code == 200
            assert "Secure attachment" in query_res.json()["response"]
            
        # 5. Query with no matching context (should return generic fallback)
        query_empty = client.post(
            "/api/v1/knowledge/query",
            headers=headers,
            json={"query": "What is the capital of France?"}
        )
        assert query_empty.status_code == 200
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

def test_knowledge_query_relevancy_threshold(temp_knowledge_dir):
    # Overwrite auth dependencies
    app.dependency_overrides[get_current_user] = lambda: {"sub": "portal"}
    
    client = TestClient(app)
    token = create_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        mock_ingestor = MagicMock()
        def mock_hybrid_search(query, n_results=6):
            if config.RAG_RELEVANCY_THRESHOLD <= 0.5:
                return [{
                    "text": "Attachment styles determine how individuals react in relationships.",
                    "metadata": {"document_id": "test_doc", "chunk_index": 0, "title": "Attachment Styles Overview", "author": "Mary Ainsworth", "year": 1978},
                    "similarity": 0.50
                }]
            return []
        mock_ingestor.hybrid_search.side_effect = mock_hybrid_search
        
        with patch('src.api.api_knowledge.KnowledgeIngestor', return_value=mock_ingestor), \
             patch('src.api.api_knowledge.llm_dispatcher') as mock_llm:
            mock_llm.dispatch.return_value = "Secure attachment style leads to trusting relationships [1]."
            
            # Query when config.RAG_RELEVANCY_THRESHOLD is default (0.3) -> should succeed
            config.RAG_RELEVANCY_THRESHOLD = 0.3
            query_res = client.post(
                "/api/v1/knowledge/query",
                headers=headers,
                json={"query": "What does secure attachment style lead to?"}
            )
            assert query_res.status_code == 200
            assert "Secure attachment" in query_res.json()["response"]
            assert len(query_res.json()["citations"]) == 1

            # Query when config.RAG_RELEVANCY_THRESHOLD is high (0.8) -> should be filtered out
            config.RAG_RELEVANCY_THRESHOLD = 0.8
            query_res_filtered = client.post(
                "/api/v1/knowledge/query",
                headers=headers,
                json={"query": "What does secure attachment style lead to?"}
            )
            assert query_res_filtered.status_code == 200
            assert "I am sorry, but that information is not available" in query_res_filtered.json()["response"]
            assert len(query_res_filtered.json()["citations"]) == 0
            
    finally:
        app.dependency_overrides.clear()
        config.RAG_RELEVANCY_THRESHOLD = 0.3

def test_knowledge_query_condensation(temp_knowledge_dir):
    # Overwrite auth dependencies
    app.dependency_overrides[get_current_user] = lambda: {"sub": "portal"}
    
    client = TestClient(app)
    token = create_jwt_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        mock_ingestor = MagicMock()
        mock_ingestor.hybrid_search.return_value = [
            {
                "text": "Attachment styles determine how individuals react in relationships.",
                "metadata": {"document_id": "test_doc", "chunk_index": 0, "title": "Attachment Styles Overview", "author": "Mary Ainsworth", "year": 1978},
                "similarity": 0.90
            }
        ]
        
        with patch('src.api.api_knowledge.KnowledgeIngestor', return_value=mock_ingestor), \
             patch('src.api.api_knowledge.llm_dispatcher') as mock_llm:
            
            # Mock return values for LLM dispatcher: first call is query condensation, second is grounded Q&A
            mock_llm.dispatch.side_effect = [
                "Explain Sue Johnson's attachment theory in detail.", # Condensed query
                "Here is an explanation of the attachment theory [1]." # Final answer
            ]
            
            payload = {
                "query": "Explain more.",
                "history": [
                    {"sender": "user", "text": "What is Sue Johnson's theory?"},
                    {"sender": "assistant", "text": "Sue Johnson is known for Emotionally Focused Therapy and attachment theory."}
                ]
            }
            
            query_res = client.post(
                "/api/v1/knowledge/query",
                headers=headers,
                json=payload
            )
            assert query_res.status_code == 200
            assert "explanation of the attachment theory" in query_res.json()["response"]
            
            # Check that query condensation was triggered with correct prompt containing history
            assert mock_llm.dispatch.call_count == 2
            first_call_args = mock_llm.dispatch.call_args_list[0]
            first_prompt = first_call_args[1]["prompt"]
            assert "User: What is Sue Johnson's theory?" in first_prompt
            assert "Assistant: Sue Johnson is known for Emotionally Focused Therapy" in first_prompt
            assert "Follow-up Question: Explain more." in first_prompt

            # Check that the second call (Q&A) was queried with the condensed query
            second_call_args = mock_llm.dispatch.call_args_list[1]
            second_prompt = second_call_args[1]["prompt"]
            assert "Practitioner's Question: Explain Sue Johnson's attachment theory in detail." in second_prompt

    finally:
        app.dependency_overrides.clear()

def test_scanned_pdf_detection(temp_knowledge_dir):
    from src.engine.knowledge_ingestor import KnowledgeIngestor
    ingestor = KnowledgeIngestor()
    dummy_pdf = temp_knowledge_dir / "dummy_path.pdf"
    dummy_pdf.write_text("some dummy content")
    
    with patch.object(ingestor, 'extract_pages', return_value=[(1, ""), (2, "   "), (3, "\n")]):
        with pytest.raises(ValueError, match="Scanned or image-only PDF detected"):
            ingestor.process_and_ingest(
                source_path=dummy_pdf,
                title="Scanned book",
                author="Unknown",
                year=2000
            )

def test_docx_ingestion(temp_knowledge_dir):
    from src.engine.knowledge_ingestor import KnowledgeIngestor
    from unittest.mock import mock_open
    ingestor = KnowledgeIngestor()
    
    mock_paragraphs = [MagicMock(text=f"Paragraph {i}") for i in range(100)]
    mock_doc = MagicMock(paragraphs=mock_paragraphs)
    
    with patch('docx.Document', return_value=mock_doc), \
         patch('shutil.copy2'), \
         patch('builtins.open', mock_open(read_data=b"dummybytes")), \
         patch.object(ingestor.collection, 'add') as mock_chroma_add:
         
        doc_id = ingestor.process_and_ingest(
            source_path=Path("dummy.docx"),
            title="Word book",
            author="Unknown",
            year=2000
        )
        assert doc_id is not None
        assert mock_chroma_add.called

def test_reindex_desync_recovery(temp_knowledge_dir):
    from src.engine.knowledge_ingestor import KnowledgeIngestor
    
    metrics = MetricsEngine()
    metrics.add_knowledge_document(
        doc_id="test_reindex_id",
        filename="reindex.pdf",
        filepath="reindex.pdf",
        title="Reindex Title",
        author="Author",
        year=2024,
        status="completed",
        total_pages=5,
        processed_pages=5
    )
    
    ingestor = KnowledgeIngestor()
    
    with patch.object(ingestor.collection, 'peek', side_effect=Exception("Dimension mismatch")), \
         patch.object(ingestor, 'resume_indexing_tasks') as mock_resume, \
         patch.object(ingestor.client, 'delete_collection') as mock_delete:
         
         ingestor._validate_embedding_dimension()
         
         assert mock_delete.called
         all_docs = metrics.get_all_knowledge_documents()
         doc_record = next(d for d in all_docs if d["document_id"] == "test_reindex_id")
         assert doc_record["embedding_status"] == "needs_reindexing"
