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
        progress_callback(20, f"Analyzing conversation logs ({total_messages} messages)…")

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

    rubric_anchors = _build_rubric_anchors(fw.get("dimensions", []))

    system_prompt = prompts["system"].format(sender_ctx=sender_ctx)

    template_vars = {
        "kb_context": kb_context,
        "name": name,
        "start_month": start_month or "Start",
        "end_month": end_month or "End",
        "total_messages": total_messages,
        "markdown_snippets": markdown_snippets,
        "sender_ctx": sender_ctx,
        "dimension_list": dim_list,
        "rubric_anchors": rubric_anchors,
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
    if not profile_text or not profile_text.strip():
        raise ValueError(
            f"LLM returned empty response for single-pass pipeline "
            f"(framework={framework_id}). "
            "The model may not support text generation or the prompt exceeded "
            "its context window."
        )
    if progress_callback:
        progress_callback(80, "LLM analysis complete, parsing results…")

    parsed = parse_assessment_output(profile_text, framework_id)

    parsed["narrative"] = _check_evidence_thresholds(
        parsed["narrative"],
        parsed.get("score_metadata"),
        total_messages,
    )

    if progress_callback:
        progress_callback(95, "Saving assessment to disk…")

    return {
        "profile_text": parsed["narrative"],
        "scores": parsed["scores"],
        "score_metadata": parsed.get("score_metadata"),
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

    kb_context, citations_meta = _retrieve_kb(framework_id, n_results=3)

    # Build rubric anchors from framework definition
    fw_modular = get_framework(framework_id)
    rubric_anchors = _build_rubric_anchors(fw_modular.get("dimensions", [])) if fw_modular else ""

    # Char budget per step type
    log_step_budget = 100000 if model_size == "small" else 200000
    context_step_budget = 50000 if model_size == "small" else 100000

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
        format_kwargs = {
            "chat_logs": logs_for_step,
            "context": context_str,
            "name": name,
            "total_messages": total_messages,
            "start_month": start_month or "Start",
            "end_month": end_month or "End",
            "rubric_anchors": rubric_anchors,
        }
        if step_id == "synthesis":
            format_kwargs["kb_context"] = kb_context
        user_prompt = step["user"].format(**format_kwargs)

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
        if not output or not output.strip():
            raise ValueError(
                f"Modular step {step_num}/{total_steps} ('{step['label']}') "
                f"returned empty output from the LLM. Aborting assessment. "
                f"The model may not support text generation or the prompt exceeded "
                f"its context window."
            )
        step_outputs[step["output_key"]] = output

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

    # Backfill scores from the scoring step if synthesis didn't include them
    if not parsed["scores"] and "scores" in step_outputs:
        scoring_parsed = parse_assessment_output(step_outputs["scores"], framework_id)
        parsed["scores"] = scoring_parsed["scores"]
        parsed["score_metadata"] = scoring_parsed.get("score_metadata")
        if not parsed["classification"]:
            parsed["classification"] = scoring_parsed["classification"]

    parsed["narrative"] = _check_evidence_thresholds(
        parsed["narrative"],
        parsed.get("score_metadata"),
        total_messages,
    )

    return {
        "profile_text": parsed["narrative"] or final_output,
        "scores": parsed["scores"],
        "score_metadata": parsed.get("score_metadata"),
        "classification": parsed["classification"],
        "citations": citations_meta,
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


def _check_evidence_thresholds(
    profile_text: str,
    score_metadata: dict[str, dict] | None,
    total_messages: int,
    min_dim_evidence: int = 3,
    min_avg_confidence: float = 0.4,
    low_message_threshold: int = 20,
) -> str:
    """Prepend evidence quality warnings to the profile text if thresholds are not met.

    Args:
        profile_text: The LLM-generated narrative text.
        score_metadata: Detailed score info with confidence/evidence_count per dimension.
        total_messages: Total number of messages analyzed.
        min_dim_evidence: Minimum evidence_count required per dimension.
        min_avg_confidence: Minimum average confidence required.
        low_message_threshold: Message count below which confidence is capped.

    Returns:
        Profile text with prepended warnings (if any).
    """
    warnings: list[str] = []

    if total_messages < low_message_threshold:
        warnings.append(
            f"LIMITATION: Only {total_messages} messages were available for analysis "
            f"(recommended minimum: {low_message_threshold}). Scores should be interpreted "
            f"with caution as the sample size is limited."
        )

    if score_metadata:
        low_evidence_dims = []
        low_conf_dims = []
        conf_sum = 0.0
        dim_count = 0

        for dim_id, meta in score_metadata.items():
            score_val = meta.get("score", 0)
            confidence = meta.get("confidence", 0.0)
            evidence_count = meta.get("evidence_count", 0)

            if 0 < evidence_count < min_dim_evidence:
                low_evidence_dims.append(dim_id)
            if 0 < confidence < 0.5:
                low_conf_dims.append(dim_id)
            if score_val > 0:
                conf_sum += confidence
                dim_count += 1

        avg_conf = conf_sum / dim_count if dim_count > 0 else 0.0
        if dim_count > 0 and avg_conf < min_avg_confidence:
            warnings.append(
                f"LIMITATION: Average confidence across dimensions is {avg_conf:.2f} "
                f"(recommended minimum: {min_avg_confidence}). Scores reflect limited "
                f"evidence and should be treated as preliminary."
            )

        if low_evidence_dims and len(low_evidence_dims) <= dim_count / 2:
            dim_names = ", ".join(low_evidence_dims)
            warnings.append(
                f"NOTE: Dimension(s) [{dim_names}] have fewer than {min_dim_evidence} "
                f"supporting evidence items. These scores should be considered tentative."
            )

    if warnings:
        warning_block = "\n\n".join(warnings)
        profile_text = f"{warning_block}\n\n---\n\n{profile_text}"

    return profile_text


def _build_rubric_anchors(dimensions: list[dict]) -> str:
    """Build a formatted rubric anchors string from dimension definitions."""
    parts: list[str] = []
    for d in dimensions:
        rubric = d.get("rubric")
        if not rubric:
            continue
        parts.append(f"--- {d['label']} ({d['id']}) ---")
        for anchor_range, description in rubric.items():
            parts.append(f"  Score {anchor_range}: {description}")
        parts.append("")
    return "\n".join(parts)


def _retrieve_kb(
    framework_id: str,
    n_results: int = 5,
    similarity_threshold: float | None = None,
) -> tuple[str, list[dict]]:
    """Retrieve psychology reference chunks relevant to the given framework."""
    if similarity_threshold is None:
        similarity_threshold = getattr(config, "RAG_RELEVANCY_THRESHOLD", 0.3)
    kb_chunks: list[dict] = []
    try:
        from src.engine.knowledge_ingestor import knowledge_ingestor

        ingestor = knowledge_ingestor
        query_text = get_kb_query(framework_id)
        kb_chunks = ingestor.hybrid_search(query_text, n_results=n_results)
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
            ref_str = f"Reference: {meta.get('author', 'Unknown')} ({meta.get('year', 0)}). {meta.get('title')}"
            if meta.get("page_number") is not None:
                ref_str += f", p. {meta['page_number']}"
            kb_context += ref_str + ".\n\n"
            citations_meta.append({
                "source_id": idx,
                "title": meta.get("title"),
                "author": meta.get("author", "Unknown"),
                "year": meta.get("year", 0),
                "page_number": meta.get("page_number"),
            })
        kb_context += "=========================================\n\n"

    return kb_context, citations_meta
