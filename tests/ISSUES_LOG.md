# Issues Log - Testing Phase

During the implementation of the automated test suite, the following issues/bugs were identified:

1. **StorageManager: Invalid Timestamp Handling**
   - **File:** `src/storage/storage_manager.py`
   - **Method:** `save_message` / `get_quarter_filename`
   - **Issue:** If an invalid timestamp (e.g., a string) is passed to `save_message`, it bypasses the `datetime.fromtimestamp` conversion but is still passed to `get_quarter_filename`, where it causes an `AttributeError: 'str' object has no attribute 'month'`.
   - **Impact:** Crash when processing malformed data.
   - **Status:** Partially mitigated - storage_manager.py now has try/except around datetime conversion.

2. **RAGEngine: Hardcoded Database Path**
   - **File:** `src/engine/rag_engine.py`
   - **Issue:** The database path `chroma_db` is hardcoded in `__init__`, making it difficult to point to a temporary test database without patching the instance.
   - **Impact:** Testing isolation is harder to achieve.
   - **Status:** Fixed - RAGEngine constructor now accepts db_path parameter.

3. **MediaProcessor: Missing Dependency Handling**
   - **File:** `src/engine/media_processor.py`
   - **Issue:** Loading Whisper models and Gemini configuration relies heavily on environment variables and presence of GPU. Failures in `setup_whisper` are logged but the class remains in a partially initialized state.
   - **Status:** Mitigated - CPU fallback added for Whisper when GPU unavailable.

## Open Architectural Issues

4. **`MetricsEngine` read methods not lock-protected**: Concurrent readers in WAL mode are generally safe, but Python sqlite3 shared connection is not thread-safe for cursor operations.

---

## v0.10.0 Findings (UI/UX Modernization)

5. **InspectorStore: backup path used module-level DATA_DIR instead of the per-instance path**
   - **File:** `src/storage/inspector_store.py`
   - **Issue:** `_backup_path()` returned `config.DATA_DIR / backup`, but the `InspectorStore` instance could be constructed with a custom `path` (e.g., in tests using `tmp_path`). This caused backups to silently be written to the wrong directory.
   - **Impact:** No data loss, but inspector backups did not live alongside the data they backed up. Tests for backup behavior failed until fixed.
   - **Status:** Fixed — `_backup_path_for(target)` now uses the instance path. Added `test_atomic_write_creates_backup` regression test.

6. **Pre-paint theme flash on first load**
   - **File:** `frontend/src/app/layout.tsx`
   - **Issue:** Without a pre-paint theme script, the page rendered with the default dark theme briefly even when the user had selected light, causing a visible flash.
   - **Status:** Fixed — inline `<script>` in `<head>` reads `localStorage.getItem('pg.theme')` and sets `data-theme` before paint.

---

## v0.11.0 Findings (Panel Rebuilds + a11y)

7. **Inspector note "edit" affordance used a non-interactive `<p>` with onClick**
   - **File:** `frontend/src/components/Inspector.tsx`
   - **Issue:** The note body was rendered as a `<p onClick={...}>` to trigger edit mode. This is a well-known a11y anti-pattern — keyboard and screen-reader users cannot focus or activate it.
   - **Impact:** Notes were uneditable via keyboard. Caught by `jsx-a11y/no-noninteractive-element-interactions` in v0.11.0.
   - **Status:** Fixed — replaced with `<button type="button">` that has an explicit focusable style and the same click handler.

8. **AI Engine Router section used a `<label>` without `htmlFor`**
   - **File:** `frontend/src/components/AIHub.tsx`
   - **Issue:** The "AI Engine Router" header was a `<label>` not associated with any control. Caught by `jsx-a11y/label-has-associated-control`.
   - **Status:** Fixed — replaced with `<fieldset>` + `<legend>`, which is the correct semantic for a group of related controls.

9. **Login portal label was not associated with its input**
   - **File:** `frontend/src/app/page.tsx`
   - **Issue:** `<label>Access Password</label>` had no `htmlFor`; the input had no `id`. Caught by `jsx-a11y/label-has-associated-control`.
   - **Status:** Fixed — `htmlFor="portal-password"` paired with `id="portal-password"`.

10. **Import drag-and-drop zone was keyboard-inaccessible**
    - **File:** `frontend/src/components/ImportPanel.tsx`
    - **Issue:** The drop zone was a `<div>` with `onDrop` / `onDragOver` / `onDragLeave` but no keyboard equivalent.
    - **Status:** Fixed — added `role="button"`, `tabIndex={0}`, and Enter/Space keyboard handler that focuses the path input as the keyboard equivalent.

11. **Pre-existing lint errors not caused by v0.10.0/v0.11.0 work**
    - **Files:** `GlobalSearch.tsx` (refs-during-render), `ProgressPanel.tsx` (Date.now in render), several unused-import warnings.
    - **Status:** Out of scope for the modernization. Pre-existing. Tracked for follow-up.

---

## v0.11.1 Findings (Pre-existing lint cleanup)

12. **GlobalSearch.tsx: ref mutated during render**
    - **File:** `frontend/src/components/GlobalSearch.tsx`
    - **Issue:** `isOpenRef.current = isGlobalSearchOpen` was executed during render to keep a ref in sync, violating React's purity rule. Blocked by `react-hooks/refs` lint rule.
    - **Status:** Fixed — removed the ref entirely; the keydown handler now reads `isGlobalSearchOpen` directly from the closure (added to the effect's dependency array).

13. **ProgressPanel.tsx TaskRow: `Date.now()` during render**
    - **File:** `frontend/src/components/ProgressPanel.tsx`
    - **Issue:** `TaskRow` called `Date.now()` to compute elapsed time during render, violating the component-purity rule. Blocked by `react-hooks/purity` lint rule.
    - **Status:** Fixed — added a `useTickingNow(1000)` hook at the parent that ticks once per second; `TaskRow` now receives `nowMs` as a prop. The parent's clock display reuses the same `nowMs` (via `new Date(nowMs).toLocaleTimeString(...)`).

14. **Math.random() in Skeleton component during render**
    - **File:** `frontend/src/components/ui/Skeleton.tsx`
    - **Issue:** `ContactListSkeleton` and `MessageThreadSkeleton` used `Math.random()` to vary skeleton widths. Same purity violation.
    - **Status:** Fixed — replaced with deterministic width arrays cycled by index. No randomness.

15. **`any` type in `useDebounce` generic**
    - **File:** `frontend/src/lib/useDebounce.ts`
    - **Issue:** `T extends (...args: any[]) => void` triggered `@typescript-eslint/no-explicit-any`.
    - **Status:** Fixed — generic changed to `T extends (...args: never[]) => void` (the `never[]` trick preserves caller-side type inference while satisfying the lint rule).

16. **Unused imports and `const` declarations across the codebase**
    - **Files:** `page.tsx` (`useRagStore`), `AIHub.tsx` (`useCallback`), `Header.tsx` (`ChevronDown`), `Inspector.tsx` (`Note`, `ChevronRight`, `MIN_WIDTH`, `MAX_WIDTH`), `Workspace.tsx` (`useCallback`), `api.ts` (`RAW_API_BASE`), `authStore.ts` (`AuthError`, `AppError`), `contactsStore.ts` (`SystemStatus`), `taskStore.ts` (`getApiBase`).
    - **Status:** Fixed — all unused imports/values removed.

17. **`no-onchange` lint warnings on `<select>` elements (false positives)**
    - **Files:** `AIHub.tsx` (Start/End Month), `SettingsPanel.tsx` (LLM Provider), `Workspace.tsx` (Sort dropdown).
    - **Issue:** The `jsx-a11y/no-onchange` rule is intended for `<input>` where `onBlur` is more accessible; it fires on `<select>` even though `onChange` is the only correct event.
    - **Status:** Fixed — added `eslint-disable-next-line jsx-a11y/no-onchange` comments with rationale (`<select> requires onChange`).

18. **Lint warnings on `autoFocus` for login + Inspector note editor**
    - **Files:** `app/page.tsx` (password input), `components/Inspector.tsx` (note textarea).
    - **Status:** Fixed — added scoped eslint-disable comments with rationale (single-input login, user-initiated edit mode).

---

## v1.0.0 Findings (UI/UX Modernization GA)

19. **Modal backdrop close without keyboard support**
    - **Files:** `GlobalSearch.tsx`, `Onboarding.tsx`, `ShortcutsModal.tsx`.
    - **Issue:** Modal backdrops used `onClick` for click-to-close but had no keyboard equivalent. `jsx-a11y/no-noninteractive-element-interactions` and `jsx-a11y/click-events-have-key-events` both fired.
    - **Status:** Fixed — added `tabIndex={-1}`, `onKeyDown` for Enter/Space to close on backdrop focus, and Escape handling via `useEffect` on the window. Modal pattern is documented in a single eslint-disable comment per file with rationale.

20. **Final token migration gaps (v0.11.0 → v1.0.0)**
    - **Files:** `GlobalSearch.tsx`, `Toast.tsx`, `AIHub.tsx` (assessment setup, profile display, RAG chat).
    - **Issue:** These files still used legacy `bg-[rgba(...)]`, `text-zinc-*`, `bg-zinc-*` classes despite the design system rollout in v0.10.0/v0.11.0.
    - **Status:** Fixed — all three files now reference only design tokens. Verified in the v1.0.0 migration status table in `frontend/docs/DESIGN.md`.

21. **Inspector Zustand selectors returned new references every render**
    - **File:** `frontend/src/components/Inspector.tsx`
    - **Issue:** The `tags`, `notes`, and `flags` selectors used inline `[]` and `{ starred: false, archived: false }` fallbacks. When `selectedContact` was `null` or the contact had no data, each render produced a new array/object reference, causing Zustand to notify a state change and triggering an infinite re-render loop (`Maximum update depth exceeded` / `getSnapshot should be cached`).
    - **Impact:** App crashed on the home screen as soon as the Inspector mounted.
    - **Status:** Fixed — moved fallback values to module-level constants (`EMPTY_TAGS`, `EMPTY_NOTES`, `DEFAULT_FLAGS`) so selectors return stable references across renders. Verified with `npm run lint`.

22. **Ambient glow divs caused document scrollHeight expansion, hiding the header**
    - **Files:** `frontend/src/app/layout.tsx`, `frontend/src/components/Workspace.tsx`, `frontend/src/components/AIHubRAGChat.tsx`
    - **Issue:** The two `<div class="ambient-glow">` elements were direct children of `<body>` with the cyan glow using `-bottom-40` (`bottom: -160px`). This extended `body`'s scrollable height by 160px. When `Workspace.tsx` called `scrollIntoView()` on message load after selecting a contact, the browser scrolled the entire document (overriding `overflow: hidden`), pushing the `relative`-positioned header off-screen. The Home button, logo, and breadcrumbs became invisible.
    - **Impact:** Header disappeared and status bar appeared to shift when selecting any contact.
    - **Status:** Fixed — wrapped ambient glows in a `fixed inset-0 overflow-hidden pointer-events-none` container so they don't affect body's scrollHeight. Added `block: 'nearest'` to `scrollIntoView` in `Workspace.tsx` and `AIHubRAGChat.tsx` to prevent accidental document scrolling. Verified with `npm run lint` and `npm run build`.

23. **Consolidated navigation: removed Header, expanded Sidebar**
    - **Files:** `frontend/src/components/Sidebar.tsx`, `frontend/src/components/Header.tsx` (deleted), `frontend/src/app/page.tsx`, `frontend/src/components/Onboarding.tsx`
    - **Issue:** The application had two separate navigation areas — a 56px top Header (brand, Home, breadcrumbs, search, user menu with Import/Settings/Theme/Shortcuts/Tour/Logout) and a 100px left Sidebar (Logout only). This split was confusing, wasted space, and the sidebar appeared empty because its only item was pushed to the bottom by a `flex-1` spacer.
    - **Impact:** Users could not discover navigation items. The sidebar was visually blank.
    - **Status:** Fixed — removed `Header.tsx` entirely. Rewrote `Sidebar.tsx` as a 64px icon rail containing: brand logo, Home, Search (⌘K), Import, Settings, Theme toggle, Cloud/Local status dots, Keyboard Shortcuts, Welcome Tour, and Logout. Updated `page.tsx` to remove Header import/usage. Updated `Onboarding.tsx` text to reference sidebar instead of "user menu". Verified with `npm run lint` and `npm run build`.

24. **Hardcoded zinc/rgba colors broke light theme in Workspace.tsx**
     - **File:** `frontend/src/components/Workspace.tsx`
     - **Issue:** 24+ hardcoded Tailwind color classes (`bg-zinc-900`, `border-zinc-800`, `text-zinc-400`, `bg-[rgba(10,10,12,0.6)]`, etc.) were used instead of CSS design tokens. These dark-only colors produced visual chaos when toggling to light theme — dark blobs, invisible text, mismatched borders.
     - **Impact:** Light theme was unusable in the Workspace panel (contacts list, chat viewer, message bubbles, pagination, monthly tabs).
     - **Status:** Fixed — replaced all 24 hardcoded colors with design tokens (`var(--bg-surface)`, `var(--bg-surface-raised)`, `var(--bg-surface-inset)`, `var(--border-subtle)`, `var(--border-strong)`, `var(--text-primary)`, `var(--text-secondary)`, `var(--text-muted)`, `var(--brand-primary-soft)`). Verified `text-white`/`text-black` on colored backgrounds (`var(--brand-primary)`, `var(--success)`) is intentional and passes AA contrast. Verified with `npm run lint` and `npm run build`.

---

## v1.0.x Findings (Instagram Import Audit)

25. **RAG chunk_id comment leaks into chat UI as visible HTML-escaped text**
    - **File:** `src/services/contacts_service.py:124`
    - **Issue:** `html.escape(body_text)` double-escapes the `<!-- chunk_id: XXXX -->` comment written to markdown by `storage_manager.py:121`. The frontend renders it in a `<p>` tag verbatim, producing `&lt;!-- chunk_id: 130faed1 --&gt;` in every message bubble.
    - **Impact:** User-facing data pollution; every message bubble shows a spurious `&lt;!-- chunk_id: ... --&gt;` string.
    - **Status:** Fixed — `parse_monthly_messages` now strips chunk_id lines from body_lines before html.escape.

26. **Non-text/non-audio content types silently dropped**
    - **File:** `src/engine/data_importer.py:33-35`
    - **Issue:** `is_supported_json_message` filters out any message containing `photos`, `videos`, or `gifs` unless accompanied by `audio_files`. Reactions, mentions, URLs, link_previews, polls, location, and stickers are never read from the JSON.
    - **Impact:** Users importing "all messages" actually lose photos, videos, GIFs, reactions, polls, location shares, and stickers. No warning is surfaced.
    - **Status:** Documented — import stats now surface dropped counts in the task tracker payload (finding #30 below). Full content support deferred to a later schema change.

27. **No UI state for pending transcriptions**
    - **File:** `src/engine/transcription_queue.py`
    - **Issue:** Audio messages show `[Audio Transcription: Processing...]` placeholder text until transcription completes. No polling, no WebSocket push, no "transcribing" badge. User must re-navigate to the month to see the result.
    - **Status:** Fixed — `contacts_service.py` now returns `audio_status` field (`pending` / `transcribed` / `failed`); `Workspace.tsx` shows a small status badge.

28. **No retry / dead-letter handling for failed transcriptions**
    - **File:** `src/engine/media_processor.py:133`
    - **Issue:** If Gemini and Whisper both fail, the transcription is permanently stamped `"Transcription failed."` with no retry mechanism. Orphaned `[Audio Transcription: Processing...]` placeholders survive a process restart.
    - **Impact:** Permanently untranscribed voicemails; user has no way to re-trigger transcription.
    - **Status:** Fixed — `TranscriptionQueue._init` now scans for orphaned placeholders and re-enqueues them. Atomic write added to prevent file corruption on crash.

29. **Audio transcription in-place rewrite not transactional**
    - **File:** `src/engine/transcription_queue.py:84`
    - **Issue:** The worker reads the full `.md` file, mutates the block in memory, then writes back with `open(..., "w")`. A crash between read and write loses the entire monthly file.
    - **Impact:** Potential total data loss of a month's conversations on transcription crash.
    - **Status:** Fixed — replaced with `write → tmp → os.replace` atomic pattern.

30. **Import endpoint missing from backend**
    - **File:** `src/api/api_contacts.py` (missing endpoint)
    - **Issue:** The frontend (`ImportPanel.tsx:41`) sends `POST /api/v1/contacts/import` but no route was defined. Users always see a 404 error.
    - **Impact:** Import via the UI is entirely broken.
    - **Status:** Fixed — added `POST /api/v1/contacts/import` route that runs the import in a background thread.

31. **`is_self` flag requires INSTAGRAM_USERNAME to be configured**
    - **File:** `src/services/contacts_service.py:116-118`
    - **Issue:** If `INSTAGRAM_USERNAME` is not set, no message is ever flagged as "Me" — every bubble shows the raw sender name. The frontend has no way to know the config is missing.
    - **Impact:** Users who skip setup see "other user" labels on both sides of every conversation.
    - **Status:** Fixed — `settings_manager.py` now exposes `instagram_username` in the settings response; `contacts_service.py` returns `has_username_config`; the frontend can show a banner.

32. **Latin1→utf8 round-trip unsafe for supplementary-plane characters**
    - **File:** `src/engine/data_importer.py:205, 220, 234`
    - **Issue:** `.encode('latin1').decode('utf8')` raises `UnicodeEncodeError` for any character outside the BMP (e.g., emoji ZWJ sequences, rare scripts). The message is logged and silently skipped.
    - **Impact:** Certain emoji and non-BMP text are dropped.
    - **Status:** Fixed — added `try/except UnicodeEncodeError` with fallback to `str(raw)`. Message is logged but not dropped.

33. **Translation stubs for stats visible to frontend**
    - **File:** `src/engine/data_importer.py:282`
    - **Issue:** `task_tracker.complete_task(task_id)` now passes a stats payload (`{"scanned": N, "imported_text": N, "imported_audio": N, "dropped_reel": N, "dropped_media_only": N, "dropped_empty": N}`) so the UI can surface per-category counts.
    - **Status:** Fixed — stats attached to the completed task.

34. **Timezone not handled for timestamps**
    - **File:** `src/storage/storage_manager.py:95`
    - **Impact:** Instagram exports are UTC. `datetime.fromtimestamp` (without `tz`) uses local time, potentially bucketing messages into the wrong month.
    - **Status:** Documented as architectural debt — requires a larger schema change to address.

---

## Phase A–D Findings (Assessment Overhaul)

35. **No token budget enforcement in `/profile` endpoint**
    - **File:** `src/api/api_rag.py`
    - **Impact:** Large conversations (>15K chars) sent to Ollama would overflow its context window, producing truncated or degenerate generation.
    - **Status:** Fixed — added token budget truncation based on provider (Gemini: 300K chars, Ollama: 15K chars) with `truncated` flag in metadata.

36. **System prompt not separated from user prompt**
    - **File:** `src/engine/llm_dispatcher.py`
    - **Impact:** Safety guardrails ("DO NOT make clinical diagnoses") were sent as part of the user message rather than as a system instruction, weakening enforcement.
    - **Status:** Fixed — added `system` parameter to `dispatch()` and `dispatch_stream()`; all providers now receive safety boundaries as a proper system instruction.

37. **Multi-message chunking not implemented**
    - **File:** `src/engine/rag_engine.py`
    - **Impact:** Each Instagram DM became one ChromaDB chunk (1:1 ratio), meaning RAG queries returned at most 20 isolated messages for a 3000-message contact (0.67% coverage).
    - **Status:** Fixed — `add_messages_batch()` now groups 5 consecutive messages before chunking, reducing chunk count by ~5× and improving RAG coverage to ~3.3%.

38. **Two divergent keyword sentiment fallbacks**
    - **File:** `src/api/api_rag.py`, `src/engine/report_generator.py`
    - **Impact:** The assessment endpoint used a simpler keyword fallback without negation handling, producing different sentiment scores than the chart-generation path for the same data.
    - **Status:** Fixed — unified into shared `analyze_sentiment_keyword()` with negation-aware parsing in `report_generator.py`.

39. **KnowledgeIngestor instantiated per request**
    - **File:** `src/api/api_rag.py`
    - **Impact:** A new ChromaDB PersistentClient + embedding function was created for every profile request, wasting resources.
    - **Status:** Fixed — wrapped `KnowledgeIngestor` in `LazyProxy` singleton.

40. **No validation of month format or range**
    - **File:** `src/api/api_rag.py`
    - **Impact:** Malformed month strings (`"abc"`, `"2026_99"`) or inverted ranges (start > end) were silently accepted, producing empty results or confusing errors.
    - **Status:** Fixed — Pydantic validators now reject invalid formats and inverted ranges.

41. **PDF disclaimer contained internal rationale**
    - **File:** `src/engine/report_generator.py:577`
    - **Impact:** The disclaimer read "...This protects against liability." — an internal justification leaked into the user-facing PDF.
    - **Status:** Fixed — disclaimer now reads: "This report is AI-generated analysis based on text communication patterns. It is not a clinical or diagnostic assessment."

42. **Frontend timeout too short for profile generation**
    - **File:** `frontend/src/store/ragStore.ts`
    - **Impact:** LLM generation takes minutes but the default `apiFetch` timeout was 15 seconds, causing spurious failures.
    - **Status:** Fixed — added `timeout: 300000` (5 min) to `generateProfile()`.

43. **PDF flags not reset on contact switch**
    - **File:** `frontend/src/components/AIHub.tsx`
    - **Impact:** Switching contacts or regenerating the profile left a misleading "Download PDF" button visible from the previous compile.
    - **Status:** Fixed — `isPDFCompiled` and `isCompilingPDF` are now reset in the contact-switch `useEffect`.

44. **No retry visibility in UI**
    - **File:** `frontend/src/store/api.ts`
    - **Impact:** Network retries happened silently; users saw only the final failure without knowing a retry was attempted.
    - **Status:** Fixed — first retry now pushes an info toast.

45. **No cancel mechanism for profile generation**
    - **File:** `frontend/src/store/ragStore.ts`, `AIHubAssessment.tsx`
    - **Impact:** Users could not abort a long-running profile generation; the only way out was to close the tab.
    - **Status:** Fixed — added `AbortController` + `cancelProfileGeneration()`; Cancel button shown during generation.

## Phase 1 — Unified Model Picker (Assessment Redesign)

46. **`deep_scan` was a no-op in profile endpoint**
    - **File:** `src/api/api_rag.py`
    - **Impact:** The "Thorough Deep Scan" checkbox in assessment setup was accepted by `ProfileRequest` but never read during profile generation. Misleading UI.
    - **Status:** Fixed — `deep_scan` field removed from `ProfileRequest`. The checkbox moved from assessment setup to RAG chat panel where it IS functional (controls hybrid vector search bypass).

47. **`force_cloud` replaced by explicit model selection**
    - **File:** `src/api/api_rag.py`, `frontend/src/components/AIHub.tsx`, `AIHubAssessment.tsx`
    - **Impact:** The "Force Cloud (Gemini)" checkbox was a poor UX for controlling model routing. Users couldn't pick specific models or see which models were available from which providers.
    - **Status:** Replaced with a unified model dropdown that aggregates from all 6 providers (Ollama, Gemini, Anthropic, OpenAI, OpenCode Go/Zen). `force_cloud` retained as optional in `ProfileRequest` for backward compat.

48. **No unified model aggregation endpoint**
    - **File:** `src/api/api_models.py` (new)
    - **Impact:** Each provider's model list was siloed in test-connection endpoints. No single API to see all available models from all configured providers.
    - **Status:** Added `GET /api/v1/models` — aggregates from all 6 providers with 120s TTL cache per provider. Failed providers return errors keyed by provider name. Added `POST /api/v1/models/refresh` to invalidate cache.

49. **Model override not possible per-assessment**
    - **File:** `src/engine/llm_dispatcher.py`
    - **Impact:** Assessment always used the settings default model. Users couldn't choose a different model for a specific assessment run.
    - **Status:** Fixed — `dispatch()` now accepts `model_provider` + `model_name` params. When both are set, routes directly to the appropriate `_call_{provider}` bypassing settings-driven routing. `CloudConsentRequiredError` raised if cloud-named model selected without consent.

50. **Cloud model consent not gated by model name**
    - **File:** `src/assessment/model_size.py` (new), `src/api/api_rag.py`
    - **Impact:** Cloud-proxied models appearing in Ollama's list (e.g., `gpt-4o:latest`) were treated as local by the app, bypassing the consent check. Chat logs could reach cloud APIs without user knowledge.
    - **Status:** Fixed — Name-pattern check (`is_cloud_model()`) applied to ALL models regardless of provider. Cloud-named models from any provider gate on `user_consent`. Frontend shows inline warning + disables Generate button when cloud model selected without consent.

## Phase 2 — Framework Selection

51. **Hardcoded assessment prompts**
    - **File:** `src/assessment/prompt_templates.py` (new)
    - **Impact:** The original assessment had one hardcoded prompt for "behavioral profile report" with 4 analysis areas. No framework choice.
    - **Status:** Added 4 framework definitions (Communication Style, Big Five/OCEAN, Attachment Style, Emotional Intelligence) with per-framework system + user prompt templates. Each framework uses `<!-- SCORES: {...} -->` structured output. The `framework_id` field added to `ProfileRequest` defaults to `communication_style`.

52. **No structured output parsing**
    - **File:** `src/assessment/output_parser.py` (new)
    - **Impact:** Assessment output was free-form markdown with no way to extract dimensional scores for chart rendering.
    - **Status:** Added `parse_assessment_output()` that extracts `<!-- SCORES: {...} -->` JSON blocks and `<!-- CLASSIFICATION: ... -->` blocks from LLM responses. Scores stored in metadata JSON for future chart rendering.

53. **Static KB query across all assessments**
    - **File:** `src/assessment/kb_queries.py` (new)
    - **Impact:** The knowledge base was always queried with the same hardcoded string regardless of which type of assessment was run.
    - **Status:** Each framework definition includes a `kb_query` string (e.g., Big Five queries `"Big Five personality traits, OCEAN model..."`). Pipeline uses the framework-specific query.

## Phase 3 — Sequential Synthesis (Small-Model Pipeline)

54. **Single prompt wastes tokens on small models**
    - **File:** `src/assessment/modular_steps.py` (new)
    - **Impact:** Small models (7B-13B) received the same complex multi-section prompt as large models, forcing them to juggle multiple analytical tasks simultaneously. Quality suffered because small models can't track 4+ analytical goals in one pass.
    - **Status:** Added per-framework modular step definitions with focused single-task prompts. Communication Style and Big Five get 5 steps each, Attachment gets 6, EI gets 8. Each step asks ONE analytical question.

55. **No model size-aware routing**
    - **File:** `src/assessment/pipeline.py`
    - **Impact:** Every model went through the same single-pass pipeline regardless of capability.
    - **Status:** `run_assessment()` now calls `classify_model()` on the effective model name. Models classified as "small" or "medium" route to `run_assessment_modular()` (sequential multi-step). "Large" models use the existing single-pass pipeline. Each step reads a trimmed slice of chat logs (~6K chars for small, ~10K for medium) and prior step context, keeping per-step context under 8K tokens.


