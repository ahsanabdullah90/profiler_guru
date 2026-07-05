import os
import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from datetime import datetime
from src.utils.config import config
from src.utils.logger import logger
from src.engine.rag_engine import rag_engine
from src.engine.llm_dispatcher import llm_dispatcher, LLMDispatchError
from src.engine.settings_manager import settings_manager
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param
from src.utils.rate_limiter import RateLimiter

rag_rate_limiter = RateLimiter(requests_limit=10, window_seconds=60)

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

from fastapi.responses import StreamingResponse

@router.post("/contacts/{name}/query")
def query_contact(name: str, req: QueryRequest, current_user: dict = Depends(get_current_user), _rate_limit = Depends(rag_rate_limiter)):
    validate_safe_param(name, "contact")
    try:
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        user_tenant = current_user.get("sub", "portal")
        
        # 1. Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(name, req.start_month, req.end_month)
        
        # 2. Query hybrid search if not deep scan (incorporates tenant filter and threshold)
        vector_chunks = []
        if not req.deep_scan:
            try:
                vector_chunks = rag_engine.hybrid_query(
                    query=req.query,
                    chat_name=name,
                    start_month=req.start_month,
                    end_month=req.end_month,
                    tenant_id=user_tenant,
                    n_results=20
                )
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}")
                
        # 3. Concatenate sources
        context_parts = []
        if markdown_snippets:
            context_parts.append(f"MARKDOWN LOG SNIPPETS (Selected Range):\n{markdown_snippets}")
        if vector_chunks:
            context_parts.append("SEMANTICALLY RETRIEVED VECTOR CHUNKS:\n" + "\n---\n".join(vector_chunks))
            
        context = "\n\n=========================================\n\n".join(context_parts)
        
        # Capping context length depending on LLM selection and configurations
        max_chars = getattr(config, "RAG_TOKEN_BUDGET_GEMINI", 300000) if active_provider == "gemini" else getattr(config, "RAG_TOKEN_BUDGET_OLLAMA", 15000)
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
        def event_generator():
            # 1. Send metadata (token estimate & source months/ranges) first
            meta = {
                "type": "metadata",
                "token_estimate": token_estimate,
                "sources": []
            }
            if req.start_month or req.end_month:
                rng = f"{req.start_month or ''} to {req.end_month or ''}".strip(" to ")
                meta["sources"].append(f"Raw markdown logs ({rng})")
            elif markdown_snippets:
                meta["sources"].append("Raw markdown logs (Full range)")
                
            if vector_chunks:
                meta["sources"].append("Dense ChromaDB vectors")
                if len(vector_chunks) > 0:
                    meta["sources"].append("Sparse keyword matches (BM25)")

            yield f"data: {json.dumps(meta)}\n\n"

            try:
                # 2. Yield token chunks in real-time
                token_stream = llm_dispatcher.dispatch_stream(
                    prompt=prompt,
                    token_budget=token_estimate,
                    force_cloud=False,
                    provider=active_provider,
                    ollama_model=selected_ollama_model,
                    user_consent=req.user_consent
                )
                for token in token_stream:
                    yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
            except Exception as e:
                logger.error(f"Error streaming response: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

            yield "data: {\"type\": \"done\"}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    except LLMDispatchError as de:
        logger.error(f"LLM dispatch failed for contact {name}: {de}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "LLM_DISPATCH_FAILED",
                "message": str(de),
                "can_retry": True
            }
        )
    except Exception as e:
        logger.error(f"Error querying contact RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/{name}/profile")
def generate_profile(name: str, req: ProfileRequest, current_user: dict = Depends(get_current_user), _rate_limit = Depends(rag_rate_limiter)):
    validate_safe_param(name, "contact")
    try:
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        
        # 1. Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(name, req.start_month, req.end_month)
        
        if not markdown_snippets:
            raise HTTPException(status_code=400, detail="No message snippets found in the selected date range.")

        # 2. Enforce minimum block density validation
        from src.utils.markdown import parse_message_blocks
        raw_blocks = parse_message_blocks(markdown_snippets)
        min_blocks = getattr(config, "ASSESSMENT_MIN_BLOCKS", 5)
        total_messages = len(raw_blocks)
        
        if total_messages < min_blocks:
            raise HTTPException(
                status_code=400,
                detail=f"Chat history density is insufficient. Selected range has {total_messages} message blocks, "
                       f"but a minimum of {min_blocks} is required. Please expand the analysis range or import more DMs."
            )
            
        # 3. Grounding: Calculate average sentiment across the range
        try:
            from src.engine.report_generator import analyze_sentiment_transformer
            avg_sentiment = analyze_sentiment_transformer(raw_blocks)
        except Exception:
            avg_sentiment = None
            
        if avg_sentiment is None:
            # Urdu & English keyword fallback sentiment matching
            pos_words = {"good", "great", "awesome", "happy", "love", "nice", "best", "thanks", "thank",
                         "sweet", "perfect", "amazing", "glad", "haha", "hahaha", "accha", "acha",
                         "sahi", "khush", "shukriya", "pyar", "muhabbat", "zabardast", "umdah", "khoob", "yara"}
            neg_words = {"bad", "sad", "angry", "hate", "sorry", "worst", "broken", "hurt", "annoyed",
                         "wrong", "difficult", "boring", "disappointed", "afsos", "gussa", "nafrat",
                         "kharab", "bura", "rula", "pareshan", "ro", "rona"}
            scores = []
            for b in raw_blocks:
                words = b.lower().split()
                pos_count = sum(1 for w in words if w in pos_words)
                neg_count = sum(1 for w in words if w in neg_words)
                diff = pos_count - neg_count
                if diff > 0:
                    scores.append(1.0)
                elif diff < 0:
                    scores.append(-1.0)
                else:
                    scores.append(0.0)
            avg_sentiment = sum(scores) / len(scores) if scores else 0.0

        token_estimate = rag_engine.estimate_token_count(markdown_snippets)
        
        # 3. Retrieve relevant chunks from the psychology knowledge base (if available)
        kb_chunks = []
        try:
            from src.engine.knowledge_ingestor import KnowledgeIngestor
            ingestor = KnowledgeIngestor()
            # Generate queries based on name/context or generic psychometric terms
            results = ingestor.collection.query(
                query_texts=["linguistic style, emotional sentiment, attachment type, personality traits"],
                n_results=5
            )
            if results and results.get('documents') and results['documents'][0]:
                docs = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                for doc, meta, dist in zip(docs, metadatas, distances):
                    similarity = 1.0 - dist
                    if similarity >= 0.70:
                        kb_chunks.append({
                            "text": doc,
                            "metadata": meta,
                            "similarity": similarity
                        })
        except Exception as e:
            logger.warning(f"Could not retrieve psychology knowledge base chunks: {e}")

        kb_context = ""
        citations_meta = []
        if kb_chunks:
            kb_context = "\nRETRIEVED PSYCHOLOGY METHODOLOGY REFERENCE LITERATURE:\n"
            kb_context += "=========================================\n"
            for idx, chunk in enumerate(kb_chunks, start=1):
                meta = chunk['metadata']
                kb_context += f"[Source {idx}] \"{chunk['text']}\"\n"
                kb_context += f"Reference: {meta.get('author', 'Unknown')} ({meta.get('year', 0)}). {meta.get('title')}.\n\n"
                citations_meta.append({
                    "source_id": idx,
                    "title": meta.get('title'),
                    "author": meta.get('author', 'Unknown'),
                    "year": meta.get('year', 0)
                })
            kb_context += "=========================================\n\n"
        
        # 4. Formulate safety role-constrained prompt
        prompt = f"""
You are a highly precise linguistic communication analyst. You are NOT a clinical psychologist.
Your task is to analyze the direct message communication logs for the contact '{name}' and synthesize a structured behavioral profile report.

CRITICAL SAFETY & ROLE BOUNDARIES:
- DO NOT make clinical diagnoses or label the contact with psychiatric/mental health disorders (e.g., depression, anxiety, NPD, BPD, PTSD).
- DO NOT make predictions about the contact's real-world behavioral choices or the future of their relationships.
- Speak strictly as a text communication analyst describing style, patterns, and sentiment.

{kb_context}
GROUNDING DATA:
- Contact Name: {name}
- Analysis Range: {req.start_month or 'Start'} to {req.end_month or 'End'}
- Total Conversation message blocks: {total_messages}
- Overall Communication Sentiment Score: {avg_sentiment:.2f} (Scale: -1.0 extremely negative, 0.0 neutral, 1.0 extremely positive)

CHAT LOGS:
{markdown_snippets}

Based ONLY on the Grounding Data, Retrieved Psychology Reference Literature (if provided), and Chat Logs above, write the report addressing the following areas:
1. **Linguistic Habits & Style**: Describe word choice, sentence structure, punctuation usage, and response patterns.
2. **Communication Profile**: Describe typical conversational tone, responsiveness, and interaction patterns.
3. **Sentiment & Temperament**: Detail the observed emotional tone, positive/negative expressions, and overall sentiment trends matching the calculated Sentiment Score.
4. **Sentiments Towards User**: Describe the relationship dynamic as expressed strictly through direct conversational exchanges.

If you reference or apply any theories, scales, or methodologies from the Retrieved Psychology Literature, you MUST cite them inline using the source number (e.g., "[Source 1]").
At the very end of your response, print a "References" section listing the matching bibliography of the retrieved sources you cited.
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
            "generated_at": datetime.now().isoformat(),
            "citations": citations_meta
        }
        
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
            
        return {"profile": profile_text, "meta": meta_data, "token_estimate": token_estimate}
    except LLMDispatchError as de:
        logger.error(f"LLM dispatch failed during profiling for {name}: {de}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "LLM_DISPATCH_FAILED",
                "message": str(de),
                "can_retry": True
            }
        )
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
        user_tenant = current_user.get("sub", "portal")
        # Perform a global query across the ChromaDB collection filtered by tenant
        results = rag_engine.collection.query(
            query_texts=[req.query],
            n_results=20,
            where={"tenant_id": user_tenant}
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
