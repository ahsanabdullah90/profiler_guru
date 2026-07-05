# src/api/api_knowledge.py
import os
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel

from src.utils.config import config
from src.utils.logger import logger
from src.utils.validation import validate_safe_param
from src.api.api_dependencies import get_current_user
from src.engine.metrics_engine import MetricsEngine
from src.engine.knowledge_ingestor import KnowledgeIngestor
from src.engine.llm_dispatcher import llm_dispatcher

router = APIRouter(prefix="/api/v1/knowledge", tags=["Psychology Knowledge Base"])

class QueryRequest(BaseModel):
    query: str

class CitationInfo(BaseModel):
    source_id: int
    title: str
    author: str
    year: int

class QueryResponse(BaseModel):
    response: str
    citations: List[CitationInfo]

def bg_process_ingest(temp_path_str: str, title: str, author: Optional[str], year: Optional[int], original_filename: str = ""):
    """Background worker task to run PDF chunking and embedding."""
    temp_path = Path(temp_path_str)
    try:
        ingestor = KnowledgeIngestor()
        ingestor.process_and_ingest(temp_path, title, author, year, original_filename=original_filename)
    except Exception as e:
        logger.error(f"Background ingestion worker failed for {title}: {e}")
    finally:
        # Cleanup temporary uploaded file
        if temp_path.exists():
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")

@router.get("")
def list_knowledge_documents(current_user: dict = Depends(get_current_user)):
    """Lists all uploaded documents and their embedding status."""
    try:
        metrics = MetricsEngine()
        docs = metrics.get_all_knowledge_documents()
        return {"documents": docs}
    except Exception as e:
        logger.error(f"Failed to list knowledge documents: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve knowledge documents list.")

@router.post("")
def upload_knowledge_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    author: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    current_user: dict = Depends(get_current_user)
):
    """Uploads a psychology reference document (PDF, TXT, MD) and indexes it in the background."""
    validate_safe_param(title, "title")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in [".pdf", ".txt", ".md", ".markdown"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF, TXT, or Markdown document."
        )
        
    try:
        # Write to a temporary file to read from during parsing
        fd, temp_path_str = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as temp_file:
            shutil_block = file.file.read()
            temp_file.write(shutil_block)
            
        temp_path = Path(temp_path_str)
        
        # Pre-register document in SQLite immediately as 'indexing' so user sees it in the dashboard
        import hashlib
        hasher = hashlib.sha256()
        with open(temp_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        doc_id = hasher.hexdigest()[:16]
        
        metrics = MetricsEngine()
        all_docs = metrics.get_all_knowledge_documents()
        if any(d["document_id"] == doc_id for d in all_docs):
            # Cleanup temp file and raise
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
            raise HTTPException(status_code=400, detail="This document is already uploaded and indexed.")
            
        # Spawn the background task to chunk/embed the PDF safely
        background_tasks.add_task(bg_process_ingest, temp_path_str, title, author, year, original_filename=file.filename)
        
        # Return success with document ID
        return {
            "status": "queued",
            "document_id": doc_id,
            "filename": file.filename,
            "title": title,
            "author": author,
            "year": year
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue knowledge upload: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to queue knowledge document upload: {str(e)}")

@router.delete("/{document_id}")
def delete_knowledge_document(document_id: str, current_user: dict = Depends(get_current_user)):
    """Deletes a document, removing its saved file and vectors from the database."""
    validate_safe_param(document_id, "document_id")
    try:
        ingestor = KnowledgeIngestor()
        ingestor.remove_document(document_id)
        return {"status": "success", "message": f"Document {document_id} successfully deleted."}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        logger.error(f"Failed to delete knowledge document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete knowledge document.")

@router.post("/query", response_model=QueryResponse)
def query_knowledge_base(req: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Queries the psychology knowledge base directly, enforcing strict grounding rules."""
    query_text = req.query
    
    # 1. Fetch relevant chunks from ChromaDB
    ingestor = KnowledgeIngestor()
    
    retrieved_items = []
    try:
        # We search with the query text directly
        results = ingestor.collection.query(
            query_texts=[query_text],
            n_results=6
        )
        if results and results.get('documents') and results['documents'][0]:
            docs = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for doc, meta, dist in zip(docs, metadatas, distances):
                similarity = 1.0 - dist
                if similarity >= 0.70: # Relevance similarity threshold
                    retrieved_items.append({
                        "text": doc,
                        "metadata": meta,
                        "similarity": similarity
                    })
    except Exception as e:
        logger.error(f"Vector search query failed: {e}")
        
    # De-duplicate chunks
    unique_chunks = {}
    for item in retrieved_items:
        key = f"{item['metadata']['document_id']}_{item['metadata']['chunk_index']}"
        if key not in unique_chunks or item['similarity'] > unique_chunks[key]['similarity']:
            unique_chunks[key] = item
            
    sorted_chunks = sorted(unique_chunks.values(), key=lambda x: x['similarity'], reverse=True)[:5]
    
    # 2. Handle empty fallback (if no chunks pass relevance checks)
    if not sorted_chunks:
        return QueryResponse(
            response="I am sorry, but that information is not available in the psychology knowledge base.",
            citations=[]
        )
        
    # 3. Assemble prompt with strict grounding instructions
    context_str = ""
    citations_list = []
    
    for idx, item in enumerate(sorted_chunks, start=1):
        meta = item['metadata']
        context_str += f"\n[Source {idx}] \"{item['text']}\"\n"
        context_str += f"Title: {meta['title']} | Author: {meta.get('author', 'Unknown')} | Year: {meta.get('year', 0)}\n"
        
        citations_list.append(CitationInfo(
            source_id=idx,
            title=meta['title'],
            author=meta.get('author', 'Unknown'),
            year=meta.get('year', 0)
        ))
        
    prompt = f"""
You are a highly precise psychology Q&A assistant.
Your task is to answer the user's question based strictly on the retrieved psychology literature contexts below.

CRITICAL RULES:
1. ONLY use the provided Retrieved Context to formulate your answer.
2. If the context does not contain sufficient details to fully answer the question, state politely: "I am sorry, but that information is not available in the psychology knowledge base." Do NOT invent or make up facts.
3. Every time you mention a fact or concept from a specific source, you MUST cite it using the inline source index, e.g. "[Source 1]".

Retrieved Context:
=========================================
{context_str}
=========================================

User Question: {query_text}
"""
    
    try:
        from src.engine.settings_manager import settings_manager
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        
        response_text = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=len(prompt), # Standard budget
            force_cloud=(active_provider == "gemini"),
            provider=active_provider,
            ollama_model=selected_ollama_model,
            user_consent=True
        )
        
        # Ensure we filter out hallucinated citations
        # If the LLM generates a citation like [Source 8] when we only provided 5, strip or fix it.
        # Clean response
        import re
        max_source = len(citations_list)
        
        def filter_citations(match):
            source_num = int(match.group(1))
            if source_num > max_source:
                return "" # Strip hallucinated source
            return f"[Source {source_num}]"
            
        cleaned_response = re.sub(r'\[Source\s*(\d+)\]', filter_citations, response_text)
        
        # Also clean up double bracket footprints
        cleaned_response = cleaned_response.replace("  ", " ").strip()
        
        return QueryResponse(
            response=cleaned_response,
            citations=citations_list
        )
    except Exception as e:
        logger.error(f"Failed to generate LLM response for knowledge query: {e}")
        raise HTTPException(status_code=500, detail="Failed to synthesize Q&A response from model.")
