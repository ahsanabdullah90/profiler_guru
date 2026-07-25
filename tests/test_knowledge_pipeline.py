# tests/test_knowledge_pipeline.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from src.engine.knowledge_ingestor import KnowledgeIngestor, _detect_headings
from src.engine.metrics_engine import MetricsEngine

@pytest.fixture
def temp_knowledge_dir(tmp_path, monkeypatch):
    from src.utils.config import config
    old_data_dir = config.DATA_DIR
    config.DATA_DIR = tmp_path
    
    # Reset singleton
    MetricsEngine._instance = None
    metrics = MetricsEngine(db_path=tmp_path / "psych_profiles.db")
    
    yield tmp_path
    
    config.DATA_DIR = old_data_dir
    MetricsEngine._instance = None

def test_detect_headings():
    lines = [
        "Introduction",
        "Chapter 1: The Secure Style",
        "1.2.3 Avoidant Attachment",
        "THIS IS A SHORTER HEADER",
        "This is a longer line of text that should not count as a heading because it is too long and descriptive.",
        "Brief"
    ]
    headings = _detect_headings(lines)
    assert "Chapter 1: The Secure Style" in headings
    assert "1.2.3 Avoidant Attachment" in headings
    assert "THIS IS A SHORTER HEADER" in headings
    assert "This is a longer line of text that should not count as a heading because it is too long and descriptive." not in headings

def test_extract_pages_txt(temp_knowledge_dir):
    dummy_file = temp_knowledge_dir / "test.txt"
    dummy_file.write_text("Hello attachment theory.", encoding="utf-8")
    
    ingestor = KnowledgeIngestor()
    pages = ingestor.extract_pages(dummy_file)
    assert len(pages) == 1
    assert pages[0] == (0, "Hello attachment theory.")

@patch("pdfplumber.open")
def test_extract_pages_pdf(mock_pdf_open, temp_knowledge_dir):
    # Set up mocked pdfplumber page structure
    mock_pdf = MagicMock()
    mock_page1 = MagicMock()
    mock_page1.page_number = 1
    mock_page1.extract_text.return_value = "Chapter 1: Security\nThis is a short line\nSome paragraph text here."
    
    mock_page2 = MagicMock()
    mock_page2.page_number = 2
    mock_page2.extract_text.return_value = "1.2 avoidant style\nHello avoidance."
    
    mock_pdf.pages = [mock_page1, mock_page2]
    mock_pdf_open.return_value.__enter__.return_value = mock_pdf
    
    dummy_pdf = temp_knowledge_dir / "test.pdf"
    dummy_pdf.touch()
    
    ingestor = KnowledgeIngestor()
    pages = ingestor.extract_pages(dummy_pdf)
    assert len(pages) == 2
    assert pages[0][0] == 1
    assert "Chapter 1: Security" in pages[0][1]
    assert pages[1][0] == 2
    assert "1.2 avoidant style" in pages[1][1]

def test_process_and_ingest_progress(temp_knowledge_dir):
    dummy_file = temp_knowledge_dir / "test.txt"
    dummy_file.write_text("Line 1 text. Line 2 text.", encoding="utf-8")
    
    ingestor = KnowledgeIngestor()
    
    with patch.object(ingestor.collection, "add") as mock_add:
        doc_id = ingestor.process_and_ingest(dummy_file, "Attachment Overview", "Sue Johnson", 2019)
        assert doc_id is not None
        assert mock_add.called
        
        # Verify SQLite progress is complete
        docs = ingestor.metrics_engine.get_all_knowledge_documents()
        assert len(docs) == 1
        assert docs[0]["document_id"] == doc_id
        assert docs[0]["total_pages"] == 1
        assert docs[0]["processed_pages"] == 1
        assert docs[0]["embedding_status"] == "completed"

def test_resume_indexing_tasks(temp_knowledge_dir):
    dummy_file = temp_knowledge_dir / "test.txt"
    dummy_file.write_text("Interrupted data.", encoding="utf-8")
    
    ingestor = KnowledgeIngestor()
    
    # Pre-register document as stuck in indexing state
    doc_id = "test_doc_resume"
    saved_path = ingestor.storage_dir / f"{doc_id}_test_resume.txt"
    saved_path.write_text("Interrupted data.", encoding="utf-8")
    
    ingestor.metrics_engine.add_knowledge_document(
        doc_id=doc_id,
        filename="test_resume.txt",
        filepath=str(saved_path),
        title="Interrupted Doc",
        author="Unknown",
        year=2020,
        status="indexing",
        total_pages=5,
        processed_pages=2
    )
    
    # Verify it is returned as interrupted
    interrupted = ingestor.metrics_engine.get_interrupted_knowledge_documents()
    assert len(interrupted) == 1
    assert interrupted[0]["document_id"] == doc_id
    
    with patch.object(ingestor, "process_and_ingest") as mock_process, \
         patch.object(ingestor.collection, "delete") as mock_delete:
         
        ingestor.resume_indexing_tasks()
        
        # Wait a brief moment for background thread startup
        import time
        time.sleep(0.1)
        
        # Should delete partial vectors and trigger process_and_ingest again
        assert mock_delete.called
        assert mock_process.called
