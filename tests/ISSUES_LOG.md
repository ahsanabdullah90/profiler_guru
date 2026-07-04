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

