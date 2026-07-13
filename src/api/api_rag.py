import json
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from src.api.api_dependencies import get_current_user, resolve_contact
from src.assessment.frameworks import DEFAULT_FRAMEWORK
from src.assessment.model_size import is_cloud_model
from src.assessment.output_parser import is_error_profile
from src.assessment.pipeline import run_assessment
from src.assessment.assessment_queue import assessment_queue, QueueFull
from src.engine.llm_dispatcher import CloudConsentRequiredError, LLMDispatchError, llm_dispatcher
from src.engine.rag_engine import rag_engine
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.logger import logger
from src.utils.rate_limiter import RateLimiter
from src.utils.validation import validate_safe_param

rag_rate_limiter = RateLimiter(requests_limit=10, window_seconds=60)
assessment_rate_limiter = RateLimiter(requests_limit=2, window_seconds=300)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG & AI"])

class QueryRequest(BaseModel):
    query: str
    start_month: str | None = None
    end_month: str | None = None
    deep_scan: bool = False
    user_consent: bool = False

class ProfileRequest(BaseModel):
    start_month: str = Field(max_length=16)
    end_month: str = Field(max_length=16)
    framework_id: str = DEFAULT_FRAMEWORK
    model_provider: str | None = None
    model_name: str | None = None
    user_consent: bool = False
    force_cloud: bool = False
    deep_scan: bool = False

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_format(cls, v: str) -> str:
        if not re.match(r"^\d{4}_\d{2}$", v):
            raise ValueError(f"Month must be in format YYYY_MM (e.g., 2026_04), got: {v}")
        return v

    @model_validator(mode="after")
    def validate_range(self):
        if self.start_month > self.end_month:
            raise ValueError(f"start_month ({self.start_month}) must be <= end_month ({self.end_month})")
        return self

class GlobalSearchRequest(BaseModel):
    query: str

from fastapi.responses import StreamingResponse


@router.post("/contacts/{name}/query")
def query_contact(name: str, req: QueryRequest, current_user: dict = Depends(get_current_user), _rate_limit = Depends(rag_rate_limiter)):
    cid, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    validate_safe_param(chat_name, "contact")
    try:
        active_provider = settings_manager.get_setting("cloud_provider", "gemini")
        selected_ollama_model = settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)
        user_tenant = current_user.get("sub", "portal")

        # 1. Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(chat_name, req.start_month, req.end_month)

        # 2. Query hybrid search if not deep scan (incorporates tenant filter and threshold)
        vector_chunks = []
        if not req.deep_scan:
            try:
                vector_chunks = rag_engine.hybrid_query(
                    query=req.query,
                    chat_name=chat_name,
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

        insta_user = config.INSTAGRAM_USERNAME or ""
        sender_context = f"The user (you) has Instagram username: {insta_user}. Messages from '{insta_user}' in the chat history are your own messages." if insta_user else ""
        prompt = f"""
You are an AI assistant analyzing Instagram DMs.
Use the following chat history context (comprising raw markdown logs and semantic search snippets) to answer the user's question accurately.
If the answer is not contained in the context, synthesize the best possible response from the snippets or state that it is not explicitly mentioned.

{sender_context}

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

@router.get("/contacts/{name}/token_estimate")
def get_token_estimate(name: str, start_month: str = "", end_month: str = "", current_user: dict = Depends(get_current_user)):
    """Fast, lightweight endpoint to calculate message blocks and token counts
    for a contact during a given timeframe. Does not read or write SQLite tables.
    """
    cid, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    try:
        # Retrieve markdown snippets
        markdown_snippets = rag_engine.fetch_markdown_snippets(chat_name, start_month or None, end_month or None)
        
        # Calculate block density
        from src.utils.markdown import parse_message_blocks
        raw_blocks = parse_message_blocks(markdown_snippets)
        block_count = len(raw_blocks)
        
        # Estimate token count
        token_estimate = rag_engine.estimate_token_count(markdown_snippets)
        
        return {
            "token_estimate": token_estimate,
            "block_count": block_count,
            "has_notes": "USER OBSERVATIONS" in markdown_snippets
        }
    except Exception as e:
        logger.error(f"Error estimating token size for contact {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/contacts/{name}/profile")
def generate_profile(name: str, req: ProfileRequest, current_user: dict = Depends(get_current_user), _rate_limit = Depends(rag_rate_limiter), _assess_rate_limit = Depends(assessment_rate_limiter)):
    """Enqueues a profile generation job for the given contact.

    Validates inputs at enqueue time (contact exists, model installed, block density)
    and returns immediately with a job_id. The actual work runs in a background
    worker thread. Poll GET .../profile/status for progress.

    Args:
        name: Contact name or UUID.
        req: ProfileRequest with start_month, end_month, framework_id, etc.

    Returns:
        {"job_id": str, "status": "queued", "position": int}

    Raises:
        400: If date range is invalid, density < minimum, model not installed.
        404: If contact not found.
        429: If queue is full.
    """
    cid, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    validate_safe_param(chat_name, "contact")
    try:
        # Determine effective provider and model
        use_explicit_model = bool(req.model_provider and req.model_name)
        active_provider = req.model_provider if use_explicit_model else settings_manager.get_setting("cloud_provider", "gemini")
        selected_model = req.model_name if use_explicit_model else settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)

        # Validate that the selected Ollama model is installed
        if active_provider == "ollama" and selected_model:
            from src.utils.ollama_client import ollama_client
            installed_models = ollama_client.get_installed_models()
            model_base = selected_model.split(":")[0]
            if not any(m.split(":")[0] == model_base for m in installed_models):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "MODEL_NOT_INSTALLED",
                        "message": f"Ollama model '{selected_model}' is not installed. Please install it or select a different model in Settings.",
                        "installed_models": installed_models,
                        "can_retry": False
                    }
                )

        # Validate block density at enqueue time
        markdown_snippets = rag_engine.fetch_markdown_snippets(chat_name, req.start_month, req.end_month)
        if not markdown_snippets:
            raise HTTPException(status_code=400, detail="No message snippets found in the selected date range.")
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

        # Enqueue the job
        job_id = assessment_queue.enqueue(
            contact_name=chat_name,
            framework_id=req.framework_id,
            start_month=req.start_month,
            end_month=req.end_month,
            model_provider=req.model_provider,
            model_name=req.model_name,
            user_consent=req.user_consent,
        )

        return {"job_id": job_id, "status": "queued", "position": 1}
    except QueueFull as qf:
        raise HTTPException(status_code=429, detail=str(qf))
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error enqueuing profile generation for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/contacts/{name}/profile/status")
def get_profile_status(name: str, current_user: dict = Depends(get_current_user)):
    """Returns the status of the latest profile generation job for a contact.

    Args:
        name: Contact name or UUID.

    Returns:
        Job status dict or {"job_id": None, "status": "not_found"}.
    """
    cid, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    validate_safe_param(chat_name, "contact")
    job = assessment_queue.get_contact_job(chat_name)
    if job is None:
        return {"job_id": None, "status": "not_found"}
    return job


@router.get("/jobs")
def list_assessment_jobs(current_user: dict = Depends(get_current_user)):
    """Returns all assessment jobs (queued, running, completed, failed, cancelled)."""
    return {"jobs": assessment_queue.get_all_jobs()}


@router.get("/jobs/{job_id}")
def get_assessment_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Returns the status of a specific assessment job by job_id."""
    job = assessment_queue.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@router.delete("/jobs/{job_id}")
def cancel_assessment_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Cancels a queued or running assessment job."""
    if not assessment_queue.cancel_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    return {"status": "cancelled", "job_id": job_id}


@router.get("/contacts/{name}/profile")
def get_saved_profile(name: str, current_user: dict = Depends(get_current_user)):
    """Retrieves the latest assessment + history list for a contact."""
    _, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    validate_safe_param(chat_name, "contact")
    contact_dir = Path(config.CHATS_DIR) / chat_name
    profile_path = contact_dir / "personality_assessment.md"
    meta_path = contact_dir / "personality_assessment.json"

    profile_text: str | None = None
    meta_data: dict | None = None

    if profile_path.exists() and meta_path.exists():
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile_text = f.read()
            with open(meta_path, encoding="utf-8") as f:
                meta_data = json.load(f)
            if not profile_text or not profile_text.strip():
                logger.warning(f"Profile for {name} is empty, treating as null")
                profile_text = None
                meta_data = None
            elif is_error_profile(profile_text):
                logger.warning(f"Profile for {name} contains error message, treating as null")
                profile_text = None
                meta_data = None
        except Exception as e:
            logger.error(f"Error loading saved profile for {name}: {e}")

    # Load assessment history
    from src.engine.metrics_engine import MetricsEngine
    _me = MetricsEngine()
    cid, lookup_name = resolve_contact(name)
    history = _me.get_assessment_history(lookup_name or chat_name)

    return {"profile": profile_text, "meta": meta_data, "history": history}


@router.get("/contacts/{name}/profile/history")
def get_assessment_history(name: str, current_user: dict = Depends(get_current_user)):
    """Returns the full assessment history for a contact."""
    cid, chat_name = resolve_contact(name)
    if chat_name is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    validate_safe_param(chat_name, "contact")
    lookup = chat_name
    from src.engine.metrics_engine import MetricsEngine
    _me = MetricsEngine()
    history = _me.get_assessment_history(lookup)
    return {"history": history}

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

            for doc, meta, doc_id in zip(documents, metadatas, ids, strict=False):
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
