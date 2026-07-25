# src/api/api_knowledge.py
import os
import tempfile
import aiofiles
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

class ChatMessageModel(BaseModel):
    sender: str
    text: str

class QueryRequest(BaseModel):
    query: str
    history: Optional[List[ChatMessageModel]] = None

class CitationInfo(BaseModel):
    source_id: int
    title: str
    author: str
    year: int
    page_number: Optional[int] = None

class QueryResponse(BaseModel):
    response: str
    citations: List[CitationInfo]

def bg_process_ingest(temp_path_str: str, title: str, author: Optional[str], year: Optional[int], original_filename: str = ""):
    """Background worker task to run PDF chunking and embedding."""
    temp_path = Path(temp_path_str)
    try:
        ingestor = KnowledgeIngestor()
        ingestor.process_and_ingest(temp_path, title, author, year, original_filename=original_filename)
    except ValueError as ve:
        logger.warning(f"Validation failed for ingestion of {title}: {ve}")
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
async def upload_knowledge_document(
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
    if suffix not in [".pdf", ".txt", ".md", ".markdown", ".docx"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Please upload a PDF, TXT, Markdown, or Word document."
        )
        
    try:
        # Write to a temporary file in chunked async stream to prevent RAM exhaustion
        fd, temp_path_str = tempfile.mkstemp(suffix=suffix)
        async with aiofiles.open(temp_path_str, "wb") as temp_file:
            while chunk := await file.read(65536):
                await temp_file.write(chunk)
            
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
        # Only block if already fully processed and completed
        if any(d["document_id"] == doc_id and d["embedding_status"] == "completed" for d in all_docs):
            # Cleanup temp file and raise
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
            raise HTTPException(status_code=400, detail="This document is already uploaded and indexed.")
            
        # Register the document immediately in SQLite connection manager
        metrics.add_knowledge_document(
            doc_id=doc_id,
            filename=file.filename,
            filepath=str(metrics.db_path.parent / "knowledge_files" / f"{doc_id}_{file.filename}"),
            title=title,
            author=author,
            year=year,
            status="indexing",
            total_pages=0,
            processed_pages=0
        )

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
    
    # Condense query if chat history exists
    if req.history:
        history_turns = []
        for msg in req.history:
            if "Welcome to the Psychology Knowledge Base Chat" in msg.text:
                continue
            role = "User" if msg.sender == "user" else "Assistant"
            history_turns.append(f"{role}: {msg.text}")
        
        if history_turns:
            history_str = "\n".join(history_turns[-5:])
            condense_prompt = f"""You are an expert query condensation assistant.
Given the chat history and the follow-up question below, rewrite the follow-up question into a standalone, complete query (in English) that contains all necessary context for searching a psychology literature database.

Chat History:
{history_str}

Follow-up Question: {query_text}

Standalone query (write ONLY the query, no extra text):"""
            try:
                from src.engine.settings_manager import settings_manager
                from src.engine.rag_engine import rag_engine
                active_provider = settings_manager.get_setting("cloud_provider", "gemini")
                selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
                
                condensed = llm_dispatcher.dispatch(
                    prompt=condense_prompt,
                    token_budget=rag_engine.estimate_token_count(condense_prompt) + 120,
                    force_cloud=(active_provider == "gemini"),
                    provider=active_provider,
                    ollama_model=selected_ollama_model,
                    user_consent=True
                )
                condensed_stripped = condensed.strip().strip('"').strip("'").strip()
                if condensed_stripped:
                    logger.info(f"Condensed query '{query_text}' to '{condensed_stripped}'")
                    query_text = condensed_stripped
            except Exception as e:
                logger.warning(f"Failed to condense query: {e}")
    
    # 1. Fetch relevant chunks from ChromaDB (hybrid search)
    ingestor = KnowledgeIngestor()
    
    retrieved_items = []
    try:
        retrieved_items = ingestor.hybrid_search(query_text, n_results=10)
    except Exception as e:
        logger.error(f"Hybrid search query failed: {e}")
        
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
        if meta.get('page_number') is not None:
            context_str += f"Page: {meta['page_number']}\n"
        
        citations_list.append(CitationInfo(
            source_id=idx,
            title=meta['title'],
            author=meta.get('author', 'Unknown'),
            year=meta.get('year', 0),
            page_number=meta.get('page_number')
        ))
        
    prompt = f"""You are a knowledgeable psychology research assistant with deep clinical expertise. A practitioner has asked you a question, and you have retrieved relevant passages from the psychology literature library below to ground your answer.

Your goal is to provide a thoughtful, insightful response that synthesizes the retrieved material into a coherent expert answer. Think carefully about the question and reason through it — do not simply quote passages.

GUIDELINES:
- Draw on the Retrieved Context as your primary source of evidence. Where you synthesize or reason across multiple sources, show your thinking.
- Cite inline using [N] (e.g., [1], [2]) whenever a specific fact, claim, or framework comes from a retrieved passage.
- If the retrieved context does not cover the question at all, say: "I am sorry, but that information is not available in the psychology knowledge base." Do NOT fabricate references or make up facts.
- Respond conversationally and with clinical depth — as an expert speaking to a fellow practitioner, not as a search engine summarizing results.
- Structure your response with clear paragraphs. Use bullet points or numbered lists only when they genuinely improve clarity (e.g., listing dimensions or stages).
- You may reason, draw connections, or offer clinical implications based on what the sources say — this is encouraged.

Retrieved Context:
=========================================
{context_str}
=========================================

Practitioner's Question: {query_text}

Your expert response:"""
    
    try:
        from src.engine.settings_manager import settings_manager
        from src.engine.rag_engine import rag_engine
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        
        response_text = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=rag_engine.estimate_token_count(prompt), # Standard budget
            force_cloud=(active_provider == "gemini"),
            provider=active_provider,
            ollama_model=selected_ollama_model,
            user_consent=True
        )
        
        # Ensure we filter out hallucinated citations
        # If the LLM generates a citation like [Source 8] or [8] when we only provided 5, strip or fix it.
        # Clean response
        import re
        max_source = len(citations_list)
        
        def filter_citations(match):
            source_num = int(match.group(1))
            if source_num > max_source:
                return "" # Strip hallucinated source
            return f"[{source_num}]"
            
        cleaned_response = re.sub(r'\[(?:Source\s*)?(\d+)\]', filter_citations, response_text)
        
        # Also clean up double bracket footprints
        cleaned_response = cleaned_response.replace("  ", " ").strip()
        
        return QueryResponse(
            response=cleaned_response,
            citations=citations_list
        )
    except Exception as e:
        logger.error(f"Failed to generate LLM response for knowledge query: {e}")
        raise HTTPException(status_code=500, detail="Failed to synthesize Q&A response from model.")

async def resume_knowledge_ingestion():
    """Called at startup to restart any interrupted ingestion jobs."""
    import asyncio
    loop = asyncio.get_event_loop()
    ingestor = KnowledgeIngestor()
    await loop.run_in_executor(None, ingestor.resume_indexing_tasks)
