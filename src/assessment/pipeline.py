"""Assessment pipeline — orchestrates framework selection, KB retrieval, LLM dispatch, and output parsing.

Routes between single-pass (large model) and modular sequential (small model) pipelines
based on model size classification.
"""

from typing import Any, Callable

from src.assessment.frameworks import DEFAULT_FRAMEWORK, get_framework
from src.assessment.kb_queries import get_kb_query
from src.assessment.model_size import classify_model
from src.assessment.modular_steps import get_modular_steps
from src.assessment.output_parser import parse_assessment_output
from src.assessment.prompt_templates import get_prompt
from src.engine.llm_dispatcher import llm_dispatcher
from src.engine.settings_manager import settings_manager
from src.utils.config import config
from src.utils.logger import logger


def run_assessment(
    name: str,
    framework_id: str,
    markdown_snippets: str,
    total_messages: int,
    avg_sentiment: float,
    token_estimate: int,
    start_month: str,
    end_month: str,
    model_provider: str | None = None,
    model_name: str | None = None,
    user_consent: bool = False,
    force_cloud: bool = False,
    ollama_model: str | None = None,
    provider: str | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Run the assessment pipeline, auto-selecting single-pass or modular based on model size."""
    fw = get_framework(framework_id)
    if not fw:
        logger.warning(f"Unknown framework '{framework_id}', falling back to '{DEFAULT_FRAMEWORK}'")
        fw = get_framework(DEFAULT_FRAMEWORK)
        framework_id = DEFAULT_FRAMEWORK

    if progress_callback:
        progress_callback(5, f"Loaded framework: {fw.get('label', framework_id)}")

    # Determine effective model name for size classification
    eff_model_name = model_name or ollama_model or ""
    model_size = classify_model(eff_model_name)

    # Route to modular pipeline for small/medium models
    if model_size in ("small", "medium"):
        logger.info(
            f"Using modular sequential pipeline for model '{eff_model_name}' "
            f"(size={model_size}, framework={framework_id})"
        )
        return run_assessment_modular(
            name=name,
            framework_id=framework_id,
            markdown_snippets=markdown_snippets,
            total_messages=total_messages,
            avg_sentiment=avg_sentiment,
            token_estimate=token_estimate,
            start_month=start_month,
            end_month=end_month,
            model_provider=model_provider,
            model_name=model_name,
            user_consent=user_consent,
            model_size=model_size,
            progress_callback=progress_callback,
        )

    return _run_single_pass(
        name=name,
        framework_id=framework_id,
        fw=fw,
        markdown_snippets=markdown_snippets,
        total_messages=total_messages,
        avg_sentiment=avg_sentiment,
        token_estimate=token_estimate,
        start_month=start_month,
        end_month=end_month,
        model_provider=model_provider,
        model_name=model_name,
        user_consent=user_consent,
        force_cloud=force_cloud,
        ollama_model=ollama_model,
        provider=provider,
        progress_callback=progress_callback,
    )


# ── Single-pass pipeline (large models) ──────────────────────────────


def _run_single_pass(
    name: str,
    framework_id: str,
    fw: dict[str, Any],
    markdown_snippets: str,
    total_messages: int,
    avg_sentiment: float,
    token_estimate: int,
    start_month: str,
    end_month: str,
    model_provider: str | None = None,
    model_name: str | None = None,
    user_consent: bool = False,
    force_cloud: bool = False,
    ollama_model: str | None = None,
    provider: str | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    if progress_callback:
        progress_callback(10, "Retrieving psychology reference literature…")
    kb_context, citations_meta = _retrieve_kb(framework_id)
    if progress_callback:
        progress_callback(20, "Analyzing conversation logs ({total_messages} messages)…")

    # Check for user-defined prompt overrides in settings
    overrides = settings_manager.get_setting("prompt_overrides", {})
    framework_override = overrides.get(framework_id, {}) if isinstance(overrides, dict) else {}
    use_override = bool(
        framework_override.get("system") and framework_override.get("user")
    )
    if use_override:
        ovr_system = framework_override["system"]
        ovr_user = framework_override["user"]
        # Validate required variables — fall back to defaults if missing
        if "{sender_ctx}" not in ovr_system:
            logger.warning(f"Prompt override for '{framework_id}' missing {{sender_ctx}} in system prompt, falling back to default")
            use_override = False
        elif "{name}" not in ovr_user or "{markdown_snippets}" not in ovr_user:
            logger.warning(f"Prompt override for '{framework_id}' missing required vars (name, markdown_snippets) in user prompt, falling back to default")
            use_override = False

    if use_override:
        prompts = {"system": ovr_system, "user": ovr_user}
        logger.info(f"Using custom prompt template for framework '{framework_id}'")
    else:
        prompts = get_prompt(framework_id)
        if not prompts:
            raise ValueError(f"No prompt templates found for framework '{framework_id}'")

    insta_user = config.INSTAGRAM_USERNAME or ""
    sender_ctx = _SENDER_CTX_FMT.format(insta_user=insta_user) if insta_user else ""

    if progress_callback:
        progress_callback(35, "Building assessment prompt…")

    dim_list = "\n".join(
        f"- {d['label']} ({d['id']}): {d['description']}"
        for d in fw["dimensions"]
    )

    system_prompt = prompts["system"].format(sender_ctx=sender_ctx)

    template_vars = {
        "kb_context": kb_context,
        "name": name,
        "start_month": start_month or "Start",
        "end_month": end_month or "End",
        "total_messages": total_messages,
        "avg_sentiment": avg_sentiment,
        "markdown_snippets": markdown_snippets,
        "sender_ctx": sender_ctx,
        "dimension_list": dim_list,
        "dimension_instructions": "",
    }
    user_prompt = prompts["user"].format(**template_vars)

    dispatch_kwargs: dict[str, Any] = {
        "prompt": user_prompt,
        "token_budget": token_estimate,
        "user_consent": user_consent,
        "system": system_prompt,
    }
    if model_provider and model_name:
        dispatch_kwargs["model_provider"] = model_provider
        dispatch_kwargs["model_name"] = model_name
    else:
        dispatch_kwargs["force_cloud"] = force_cloud
        dispatch_kwargs["provider"] = provider or "ollama"
        dispatch_kwargs["ollama_model"] = ollama_model

    if progress_callback:
        progress_callback(45, "Dispatching to LLM…")
    profile_text = llm_dispatcher.dispatch(**dispatch_kwargs)
    if progress_callback:
        progress_callback(80, "LLM analysis complete, parsing results…")

    parsed = parse_assessment_output(profile_text, framework_id)

    if progress_callback:
        progress_callback(95, "Saving assessment to disk…")

    return {
        "profile_text": parsed["narrative"],
        "scores": parsed["scores"],
        "classification": parsed["classification"],
        "citations": citations_meta,
        "framework_id": framework_id,
        "pipeline_mode": "single",
    }


# ── Modular sequential pipeline (small/medium models) ────────────────


def run_assessment_modular(
    name: str,
    framework_id: str,
    markdown_snippets: str,
    total_messages: int,
    avg_sentiment: float,
    token_estimate: int,
    start_month: str,
    end_month: str,
    model_provider: str | None = None,
    model_name: str | None = None,
    user_consent: bool = False,
    model_size: str = "small",
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """Run multi-step sequential synthesis for small/medium models.

    Each step focuses on ONE analytical task. Prior step outputs are
    accumulated as {context} for subsequent steps.
    """
    steps = get_modular_steps(framework_id)
    if not steps:
        logger.warning(
            f"No modular steps defined for '{framework_id}', "
            f"falling back to single-pass"
        )
        fw = get_framework(framework_id) or get_framework(DEFAULT_FRAMEWORK)
        return _run_single_pass(
            name=name,
            framework_id=framework_id,
            fw=fw,
            markdown_snippets=markdown_snippets,
            total_messages=total_messages,
            avg_sentiment=avg_sentiment,
            token_estimate=token_estimate,
            start_month=start_month,
            end_month=end_month,
            model_provider=model_provider,
            model_name=model_name,
            user_consent=user_consent,
            progress_callback=progress_callback,
        )

    if progress_callback:
        progress_callback(10, f"Starting {len(steps)}-step modular analysis…")

    # Char budget per step type
    log_step_budget = 6000 if model_size == "small" else 10000
    context_step_budget = 3000 if model_size == "small" else 5000

    context_parts: list[str] = []
    step_outputs: dict[str, str] = {}
    total_steps = len(steps)

    for idx, step in enumerate(steps):
        step_num = idx + 1
        step_id = step["id"]
        needs_logs = step.get("needs_logs", True)

        step_pct_start = 10 + int((idx / total_steps) * 75)
        if progress_callback:
            progress_callback(step_pct_start, f"Step {step_num}/{total_steps}: {step['label']}…")

        # Build context from prior step outputs
        context_str = "\n\n".join(context_parts) if context_parts else "No prior analysis available."

        # Truncate chat logs if needed
        logs_for_step = ""
        if needs_logs:
            logs_for_step = _truncate_to_chars(
                markdown_snippets,
                log_step_budget,
            )
        else:
            # For non-log steps, trim context to context_step_budget
            context_str = _truncate_to_chars(context_str, context_step_budget)

        logger.info(
            f"Modular step {step_num}/{total_steps}: {step['label']} "
            f"(logs={bool(logs_for_step)}, context={len(context_str)} chars)"
        )

        # Format prompts
        system_prompt = step["system"]
        user_prompt = step["user"].format(
            chat_logs=logs_for_step,
            context=context_str,
            name=name,
            total_messages=total_messages,
            avg_sentiment=avg_sentiment,
            start_month=start_month or "Start",
            end_month=end_month or "End",
        )

        # Estimate token budget for this step
        step_token_budget = len(user_prompt) + len(system_prompt) + len(logs_for_step)

        dispatch_kwargs: dict[str, Any] = {
            "prompt": user_prompt,
            "token_budget": step_token_budget,
            "user_consent": user_consent,
            "system": system_prompt,
        }
        if model_provider and model_name:
            dispatch_kwargs["model_provider"] = model_provider
            dispatch_kwargs["model_name"] = model_name

        if progress_callback:
            progress_callback(step_pct_start + 10, f"Step {step_num}/{total_steps}: Processing output…")
        output = llm_dispatcher.dispatch(**dispatch_kwargs)
        step_outputs[step_id] = output

        # Append to context for next step
        context_parts.append(f"=== {step['label']} ===\n{output}")

    if progress_callback:
        progress_callback(90, "Parsing final assessment output…")

    if progress_callback:
        progress_callback(95, "Saving assessment to disk…")

    # The final step's output is the assessment result
    final_output = step_outputs.get(steps[-1]["output_key"], "")

    # Parse the final output for structured scores
    parsed = parse_assessment_output(final_output, framework_id)

    return {
        "profile_text": parsed["narrative"] or final_output,
        "scores": parsed["scores"],
        "classification": parsed["classification"],
        "citations": [],
        "framework_id": framework_id,
        "pipeline_mode": "modular",
        "total_steps": total_steps,
    }


# ── Helpers ───────────────────────────────────────────────────────────


_SENDER_CTX_FMT = (
    " Your Instagram username is '{insta_user}'. "
    "Messages from '{insta_user}' in the chat history are your own messages."
)


def _truncate_to_chars(text: str, max_chars: int) -> str:
    """Truncate text to approximately max_chars, preserving message block boundaries."""
    if len(text) <= max_chars:
        return text
    # Try to cut at the last '---' separator before max_chars
    truncated = text[:max_chars]
    last_sep = truncated.rfind("\n---\n")
    if last_sep > max_chars // 2:
        truncated = text[: last_sep + 5]
    return truncated + "\n\n[truncated for token budget]"


def _retrieve_kb(framework_id: str, n_results: int = 5) -> tuple[str, list[dict]]:
    """Retrieve psychology reference chunks relevant to the given framework."""
    kb_chunks: list[dict] = []
    try:
        from src.engine.knowledge_ingestor import knowledge_ingestor

        ingestor = knowledge_ingestor
        query_text = get_kb_query(framework_id)
        results = ingestor.collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )
        if results and results.get("documents") and results["documents"][0]:
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            for doc, meta, dist in zip(docs, metadatas, distances, strict=False):
                similarity = 1.0 - dist
                if similarity >= 0.70:
                    kb_chunks.append({
                        "text": doc,
                        "metadata": meta,
                        "similarity": similarity,
                    })
    except Exception as e:
        logger.warning(f"Could not retrieve psychology knowledge base chunks: {e}")

    kb_context = ""
    citations_meta: list[dict] = []
    if kb_chunks:
        kb_context = "\nRETRIEVED PSYCHOLOGY METHODOLOGY REFERENCE LITERATURE:\n"
        kb_context += "=========================================\n"
        for idx, chunk in enumerate(kb_chunks, start=1):
            meta = chunk["metadata"]
            kb_context += f"[Source {idx}] \"{chunk['text']}\"\n"
            kb_context += (
                f"Reference: {meta.get('author', 'Unknown')} "
                f"({meta.get('year', 0)}). {meta.get('title')}.\n\n"
            )
            citations_meta.append({
                "source_id": idx,
                "title": meta.get("title"),
                "author": meta.get("author", "Unknown"),
                "year": meta.get("year", 0),
            })
        kb_context += "=========================================\n\n"

    return kb_context, citations_meta
