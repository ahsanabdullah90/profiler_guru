import json
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from src.api.api_dependencies import get_current_user
from src.assessment.frameworks import DEFAULT_FRAMEWORK
from src.assessment.model_size import is_cloud_model
from src.assessment.pipeline import run_assessment
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

@router.post("/contacts/{name}/profile")
def generate_profile(name: str, req: ProfileRequest, current_user: dict = Depends(get_current_user), _rate_limit = Depends(rag_rate_limiter), _assess_rate_limit = Depends(assessment_rate_limiter)):
    """Generates a behavioral profile for the given contact by analyzing their chat logs.

    The full pipeline:
    1. Fetch all raw markdown (.md) message files for the contact within the date range.
    2. Enforce minimum block density (default 5 blocks).
    3. Calculate a bilingual sentiment score (transformer or keyword fallback).
    4. Enforce token budget truncation (15K chars for local Ollama, 300K for cloud Gemini).
    5. Retrieve up to 5 psychology reference literature chunks from the knowledge base.
    6. Build a system+user prompt with safety guardrails and dispatch to the LLM.
    7. Save the profile as personality_assessment.md + .json in the contact's folder.

    Args:
        name: Contact name (validated against path-traversal regex).
        req: ProfileRequest with start_month, end_month, force_cloud, deep_scan, user_consent.

    Returns:
        {"profile": str, "meta": ProfileMeta, "token_estimate": int}

    Raises:
        400: If date range is invalid, density < minimum, or no snippets found.
        422: If month format is invalid or start > end.
        502: If LLM dispatch fails (Gemini/Ollama unreachable, empty response, etc.).
    """
    validate_safe_param(name, "contact")
    try:
        # Determine effective provider and model
        use_explicit_model = bool(req.model_provider and req.model_name)
        active_provider = req.model_provider if use_explicit_model else settings_manager.get_setting("cloud_provider", "gemini")
        selected_model = req.model_name if use_explicit_model else settings_manager.get_setting("ollama_model", config.OLLAMA_MODEL)

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
        except Exception as e:
            logger.warning(f"Sentiment transformer failed, falling back to keyword matching: {e}")
            avg_sentiment = None

        if avg_sentiment is None:
            from src.engine.report_generator import analyze_sentiment_keyword
            avg_sentiment = analyze_sentiment_keyword(raw_blocks)

        token_estimate = rag_engine.estimate_token_count(markdown_snippets)

        # 3. Enforce token budget truncation
        if use_explicit_model:
            is_cloud = is_cloud_model(req.model_name) or req.model_provider != "ollama"
            cloud_available = is_cloud and req.user_consent and config.ENABLE_CLOUD_AI
        else:
            will_use_cloud = (active_provider in ("gemini", "anthropic", "openai", "opencode_go", "opencode_zen")) or (token_estimate > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS)
            cloud_available = will_use_cloud and req.user_consent and config.ENABLE_CLOUD_AI
        max_chars = getattr(config, "RAG_TOKEN_BUDGET_GEMINI", 300000) if cloud_available else getattr(config, "RAG_TOKEN_BUDGET_OLLAMA", 15000)
        truncated = False
        if len(markdown_snippets) > max_chars:
            markdown_snippets = markdown_snippets[:max_chars] + "\n\n[Conversation truncated for token limits...]"
            truncated = True
            token_estimate = rag_engine.estimate_token_count(markdown_snippets)
            logger.info(f"Profile context truncated to {max_chars} chars (provider={'cloud' if cloud_available else 'local'})")

        # 4. Run the assessment pipeline (framework prompts, KB retrieval, dispatch, parsing)
        result = run_assessment(
            name=name,
            framework_id=req.framework_id,
            markdown_snippets=markdown_snippets,
            total_messages=total_messages,
            avg_sentiment=avg_sentiment if avg_sentiment is not None else 0.0,
            token_estimate=token_estimate,
            start_month=req.start_month,
            end_month=req.end_month,
            model_provider=req.model_provider,
            model_name=req.model_name,
            user_consent=req.user_consent,
            force_cloud=False,
            provider=active_provider if not use_explicit_model else None,
            ollama_model=selected_model if not use_explicit_model else None,
        )

        profile_text = result["profile_text"]

        # Save the assessment persistently to disk
        contact_dir = Path(config.CHATS_DIR) / name
        assessments_dir = contact_dir / "assessments"
        os.makedirs(assessments_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        fw_id = req.framework_id or "unknown"
        versioned_stem = f"{fw_id}_{timestamp}"

        meta_data = {
            "start_month": req.start_month,
            "end_month": req.end_month,
            "provider": req.model_provider or active_provider,
            "model": req.model_name or selected_model,
            "generated_at": datetime.now().isoformat(),
            "citations": result["citations"],
            "truncated": truncated,
            "model_provider": req.model_provider,
            "model_name": req.model_name,
            "framework_id": req.framework_id,
            "scores": result["scores"],
            "classification": result["classification"],
            "pipeline_mode": result.get("pipeline_mode", "single"),
            "total_steps": result.get("total_steps", 1),
            "versioned_file": f"{versioned_stem}.md",
        }

        # 1. Write versioned (timestamped) files — never overwritten
        v_profile = assessments_dir / f"{versioned_stem}.md"
        v_meta = assessments_dir / f"{versioned_stem}.json"
        with open(v_profile, "w", encoding="utf-8") as f:
            f.write(profile_text)
        with open(v_meta, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        # 2. Also write the "latest" files for backward-compatible frontend access
        latest_profile = contact_dir / "personality_assessment.md"
        latest_meta = contact_dir / "personality_assessment.json"
        tmp_profile = contact_dir / "personality_assessment.md.tmp"
        with open(tmp_profile, "w", encoding="utf-8") as f:
            f.write(profile_text)
        os.replace(tmp_profile, latest_profile)
        tmp_meta = contact_dir / "personality_assessment.json.tmp"
        with open(tmp_meta, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)
        os.replace(tmp_meta, latest_meta)

        # 3. Record in assessment_history table
        from src.engine.metrics_engine import MetricsEngine
        _me = MetricsEngine()
        _me.save_assessment_metadata(contact_name=name, meta=meta_data, file_path=str(v_profile))

        return {"profile": profile_text, "meta": meta_data, "token_estimate": token_estimate}
    except CloudConsentRequiredError as ce:
        logger.warning(f"Cloud consent required for profile generation on {name}: {ce}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "CLOUD_CONSENT_REQUIRED",
                "message": str(ce),
            }
        )
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
    """Retrieves the latest assessment + history list for a contact."""
    validate_safe_param(name, "contact")
    contact_dir = Path(config.CHATS_DIR) / name
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
        except Exception as e:
            logger.error(f"Error loading saved profile for {name}: {e}")

    # Load assessment history
    from src.engine.metrics_engine import MetricsEngine
    _me = MetricsEngine()
    history = _me.get_assessment_history(name)

    return {"profile": profile_text, "meta": meta_data, "history": history}


@router.get("/contacts/{name}/profile/history")
def get_assessment_history(name: str, current_user: dict = Depends(get_current_user)):
    """Returns the full assessment history for a contact."""
    validate_safe_param(name, "contact")
    from src.engine.metrics_engine import MetricsEngine
    _me = MetricsEngine()
    history = _me.get_assessment_history(name)
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
