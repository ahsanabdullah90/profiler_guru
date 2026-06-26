import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from datetime import datetime
from src.utils.config import config
from src.utils.logger import logger
from src.engine.rag_engine import rag_engine
from src.engine.llm_dispatcher import llm_dispatcher
from src.engine.settings_manager import settings_manager
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/rag", tags=["RAG & AI"])

class QueryRequest(BaseModel):
    query: str
    start_month: Optional[str] = None
    end_month: Optional[str] = None
    deep_scan: bool = False
    user_consent: bool = False

class ProfileRequest(BaseModel):
    start_month: str
    end_month: str
    force_cloud: bool = False
    deep_scan: bool = False
    user_consent: bool = False

class GlobalSearchRequest(BaseModel):
    query: str

@router.post("/contacts/{name}/query")
def query_contact(name: str, req: QueryRequest, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        
        # 1. Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(name, req.start_month, req.end_month)
        
        # 2. Query ChromaDB if not deep scan
        vector_chunks = []
        if not req.deep_scan:
            try:
                where_filter = {"chat_name": name}
                results = rag_engine.collection.query(
                    query_texts=[req.query],
                    n_results=20,
                    where=where_filter
                )
                if results and results.get('documents') and results['documents'][0]:
                    vector_chunks = results['documents'][0]
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
                
        # 3. Concatenate sources
        context_parts = []
        if markdown_snippets:
            context_parts.append(f"MARKDOWN LOG SNIPPETS (Selected Range):\n{markdown_snippets}")
        if vector_chunks:
            context_parts.append("SEMANTICALLY RETRIEVED VECTOR CHUNKS:\n" + "\n---\n".join(vector_chunks))
            
        context = "\n\n=========================================\n\n".join(context_parts)
        
        # Capping context length depending on LLM selection
        max_chars = 300000 if active_provider == "gemini" else 15000
        if len(context) > max_chars:
            context = context[:max_chars] + "\n\n[Context truncated for token limits...]"
            
        token_estimate = rag_engine.estimate_token_count(context)
        
        prompt = f"""
You are an AI assistant analyzing Instagram DMs.
Use the following chat history context (comprising raw markdown logs and semantic search snippets) to answer the user's question accurately.
If the answer is not contained in the context, synthesize the best possible response from the snippets or state that it is not explicitly mentioned.

CONTEXT:
{context}

USER QUESTION:
{req.query}

ANSWER:
"""
        response_text = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=token_estimate,
            force_cloud=False,
            provider=active_provider,
            ollama_model=selected_ollama_model,
            user_consent=req.user_consent
        )
        
        return {"response": response_text, "token_estimate": token_estimate}
    except Exception as e:
        logger.error(f"Error querying contact RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/{name}/profile")
def generate_profile(name: str, req: ProfileRequest, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        
        # 1. Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(name, req.start_month, req.end_month)
        token_estimate = rag_engine.estimate_token_count(markdown_snippets)
        
        if not markdown_snippets:
            raise HTTPException(status_code=400, detail="No message snippets found in the selected date range.")
            
        prompt = f"""
Analyze the following Instagram direct message logs for the contact '{name}'.
Provide a detailed psychological and behavioral assessment. Highlight their linguistic habits, communication style, emotional temperament, sentiments towards the user, and psychological profile.

CHAT LOGS:
{markdown_snippets}
"""
        profile_text = llm_dispatcher.dispatch(
            prompt=prompt,
            token_budget=token_estimate,
            force_cloud=req.force_cloud,
            provider=active_provider,
            ollama_model=selected_ollama_model,
            user_consent=req.user_consent
        )
        
        # Save the assessment persistently to disk in the contact folder
        contact_dir = Path(config.CHATS_DIR) / name
        os.makedirs(contact_dir, exist_ok=True)
        
        profile_path = contact_dir / "personality_assessment.md"
        meta_path = contact_dir / "personality_assessment.json"
        
        with open(profile_path, "w", encoding="utf-8") as f:
            f.write(profile_text)
            
        meta_data = {
            "start_month": req.start_month,
            "end_month": req.end_month,
            "provider": active_provider,
            "model": selected_ollama_model if active_provider == "ollama" else "Gemini 1.5 Flash",
            "generated_at": datetime.now().isoformat()
        }
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
            
        return {"profile": profile_text, "meta": meta_data, "token_estimate": token_estimate}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error generating profile for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contacts/{name}/profile")
def get_saved_profile(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    contact_dir = Path(config.CHATS_DIR) / name
    profile_path = contact_dir / "personality_assessment.md"
    meta_path = contact_dir / "personality_assessment.json"
    
    if not profile_path.exists() or not meta_path.exists():
        return {"profile": None, "meta": None}
        
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile_text = f.read()
        with open(meta_path, "r", encoding="utf-8") as f:
            meta_data = json.load(f)
            
        return {"profile": profile_text, "meta": meta_data}
    except Exception as e:
        logger.error(f"Error loading saved profile for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search")
def global_search(req: GlobalSearchRequest, current_user: dict = Depends(get_current_user)):
    try:
        # Perform a global query across the ChromaDB collection
        results = rag_engine.collection.query(
            query_texts=[req.query],
            n_results=20
        )
        
        matches = []
        if results and results.get('documents') and results['documents'][0]:
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            ids = results['ids'][0]
            
            for doc, meta, doc_id in zip(documents, metadatas, ids):
                matches.append({
                    "id": doc_id,
                    "document": doc,
                    "chat_name": meta.get("chat_name", "Unknown"),
                    "month": meta.get("month", "Unknown"),
                    "date_range": meta.get("date_range", "unknown")
                })
                
        return matches
    except Exception as e:
        logger.error(f"Error performing global search: {e}")
        raise HTTPException(status_code=500, detail=str(e))
