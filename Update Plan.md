# Profiler Guru – Multi‑Step Improvement Plan (Bilingual Audio & Local LLM Edition)

**Priority**: Most critical (security, Windows stability, Ollama core) → least critical (UI polish).  
Each step is self‑contained, includes implementation, testing, and documentation updates, and ends with a version bump in `version.md`.

---

## Step 1 – Privacy, Ollama Auto-Detection & Version Tracking
**Criticality**: 🔴 Highest – legal, ethical, user trust, and core LLM routing. Creates `version.md`.

### Implementation
1. **Version Tracking**: Create `version.md` in the project root:
   ```
   Version History
   [0.1.0] – 2026-06-23
   Initial project version (prior to improvements)
   ```
2. **Mandatory Consent**: Add a consent checkbox in the Streamlit sidebar (stored in `st.session_state`):
   - *"I understand that audio transcriptions and chat text may be sent to Google Gemini for cloud analysis (if Gemini is selected). I agree to this processing."*
   - If not checked, disable all Gemini cloud calls.
3. **Ollama Auto-Detection**:
   - Write a helper function in `src/utils/ollama_client.py` to query Ollama's local API (`GET http://localhost:11434/api/tags`).
   - If Ollama is running, retrieve the list of installed models.
   - Implement a ranking algorithm to auto-select the best model: `gemma2` > `llama3` > `mistral` > `phi3` > others.
4. **LLM Provider Routing**:
   - Modify the UI to show an LLM Selector: **Google Gemini (Cloud)** vs. **Detected Local Ollama Models**.
   - If Gemini is chosen but consent is denied or `ENABLE_CLOUD_AI=false`, automatically fall back to the best detected local Ollama model.
5. **Simple Authentication**: Ask for a password (env var `APP_PASSWORD`, default `instasync`) before displaying the main UI.
6. **Purge Image Logic**: Remove all references to image processing, image downloading, and image stubs in this step.

### Testing
- Verify Ollama API detection works when Ollama is running/not running.
- Mock Gemini and Ollama APIs to verify routing behaves correctly under different consent/selection states.
- Test password gate and session persistence.

### Documentation
- Update `README.md` with **Privacy Notice** and **Ollama Setup** sections.
- Add `PRIVACY.md` explaining local-first data processing.
- Update `.env.example` with `ENABLE_CLOUD_AI`, `APP_PASSWORD`, and `OLLAMA_HOST`.

### Version Update
- Append to `version.md`:
  ```
  [0.2.0] – 2026-06-23
  Added
  - Ollama local model auto-detection and ranking.
  - Hybrid routing between Gemini (cloud) and Ollama (local).
  - Mandatory privacy consent gate.
  - Simple password gate.
  - Initial version.md tracking.
  Removed
  - Image downloading and captioning.
  ```

---

## Step 2 – Windows Path & Filesystem Hardening (No Images)
**Criticality**: 🔴 High – prevents crashes, data loss, and path errors on Windows.

### Implementation
1. **Application Data Directory**: Define `get_app_data_dir()` returning `pathlib.Path` of `%LOCALAPPDATA%/InstaSync` on Windows, else `~/.instasync`.
2. **Config Update**: Add `DATA_DIR` to `Config`. Update all modules (`StorageManager`, `RAGEngine`, `InstagramSync`, `DataImporter`) to accept `data_dir: Path`.
3. **Storage Sanitization**:
   - Inside `StorageManager`, sanitize contact names: replace `< > : " / \ | ? *` with `_` and trim trailing spaces/dots.
   - **Only create `Chats/` and `Audio/` directories** under `DATA_DIR/chats/<contact_name>/`. Completely remove `Media/` folder creation and photo-copying code.
4. **ChromaDB Relocation**: Move ChromaDB persistence to `DATA_DIR/chroma_db/`.
5. **Windows Long-Path Support**: On startup, if `os.name == 'nt'`, verify/log warning if registry key `LongPathsEnabled` is missing, and prepend `\\?\` to absolute paths where needed.
6. **Pre-flight Checks**: Verify write access to `DATA_DIR` and check for at least 500 MB free disk space on startup.

### Testing
- Verify that only `Chats/` and `Audio/` folders are created (no `Media/` folder).
- Test folder creation with malformed/special-character contact names.
- Verify long-path operations work without throwing `FileNotFoundError`.

### Documentation
- Update `README.md` Windows installation section with the new default data location.
- Add `FS_STRUCTURE.md` describing the layout inside `DATA_DIR` (focusing on Chats and Audio).

### Version Update
- Append to `version.md`:
  ```
  [0.3.0] – 2026-06-23
  Changed
  - Data storage relocated to %LOCALAPPDATA%/InstaSync on Windows.
  - Storage Manager refactored to handle only text chats and audio files (images purged).
  - Folder names sanitized against Windows invalid character rules.
  Added
  - Pre-flight filesystem and disk-space checks.
  - Windows long-path prefix support.
  ```

---

## Step 3 – Bilingual RAG Core & Local LLM Integration
**Criticality**: 🟠 High – enables high-quality local/cloud retrieval and Urdu/English support.

### Implementation
1. **Bilingual Audio Transcription**:
   - Refactor `media_processor.py` to configure `faster-whisper`.
   - Set transcription to auto-detect language (fully supporting both English and Urdu).
   - Ensure the transcription prompt or configuration handles Urdu script and Roman Urdu accents.
2. **Message Chunking with Overlap**:
   - Instead of indexing entire quarterly files, split markdown logs into chunks of max 2000 characters with a 200-character overlap.
   - Attach metadata to each chunk: `chat_name`, `date_range`, and `chunk_index`.
   - Update `RAGEngine.add_messages_batch()` to split and index these chunks.
3. **Local/Cloud Hybrid RAG & Profiling**:
   - Update `RAGEngine.query()` and `analyze_profile()` to use the active LLM provider (Gemini or selected Ollama model).
   - **Heavy-Lifting Profiling**: For local profiling, retrieve the top-20 most relevant chunks for the contact, construct a detailed bilingual prompt (English + Urdu instructions), and generate the profile.
   - For Gemini, utilize its larger context window for more comprehensive analysis when selected.
4. **Embedding Check**: Explicitly set the local embedding function in ChromaDB. On startup, verify the collection dimension matches; if not, recreate the collection safely.
5. **Robust API Calls**: Wrap both Gemini and Ollama network calls in retry loops with exponential backoff (3 retries).

### Testing
- Feed bilingual (English + Urdu) text and audio files to verify correct chunking and transcription.
- Verify that profiling a contact retrieves only the most relevant chunks and formats them correctly for the active LLM (Gemini or Ollama).
- Mock Ollama/Gemini failures to verify exponential backoff retries.

### Documentation
- Update `README.md` with the chunking strategy and bilingual flow.
- Document local embedding model details in `rag_engine.py` comments.

### Version Update
- Append to `version.md`:
  ```
  [0.4.0] – 2026-06-23
  Changed
  - RAG indexing refactored to use 2000-character chunks with overlap.
  - Profiling upgraded to use retrieval-augmented top-20 chunks for both local and cloud LLMs.
  - Voice transcription upgraded to auto-detect and transcribe English and Urdu.
  Added
  - Unified LLM interface supporting both local Ollama and Google Gemini.
  - Embedding dimension validation on startup.
  - Retry-with-backoff logic for LLM APIs.
  ```

---

## Step 4 – Operational Resilience & Error Boundaries
**Criticality**: 🟠 High – prevents background thread leaks and data loss.

### Implementation
1. **Graceful Sync Thread Shutdown**:
   - Implement a `SyncManager` class that manages the background sync thread with a `threading.Event` stop flag.
   - Register an exit handler using `atexit` and Streamlit's session teardown hooks to gracefully stop and join the sync thread.
2. **Persistent Deduplication**:
   - Save a JSON file `last_sync.json` in `DATA_DIR` mapping thread IDs to their last synced message timestamp and message ID.
   - At sync startup, load this file; fetch only messages newer than the stored state.
3. **Global UI Error Boundary**:
   - Wrap the main rendering block in `streamlit_app.py` in a try/except.
   - If an unhandled exception occurs, display a user-friendly error card and log the traceback to `DATA_DIR/logs/error.log`.
4. **File-based Logging**:
   - Configure the `InstaSync` logger to write to both stdout and `DATA_DIR/logs/app.log` with size-based rotation (max 5 MB, 2 backups).

### Testing
- Simulate process termination and verify the background thread stops cleanly.
- Verify that stopping and restarting the sync does not re-fetch or duplicate messages.
- Trigger a rendering error and verify the global error card captures it without crashing the Streamlit server.

### Documentation
- Add `LOGGING.md` explaining log locations and how to read them.
- Add a troubleshooting section to `README.md`.

### Version Update
- Append to `version.md`:
  ```
  [0.5.0] – 2026-06-23
  Added
  - Graceful thread management and shutdown hooks.
  - State persistence (last_sync.json) to prevent message duplication.
  - Global Streamlit error boundary.
  - Rotating file logger in app-data directory.
  ```

---

## Step 5 – UI/UX Polish (Bilingual Search & Model Selection)
**Criticality**: 🟡 Medium – enhances usability and responsiveness.

### Implementation
1. **Streamlit Progress Indicators**:
   - Add a progress bar (`st.progress`) during historical JSON imports.
   - Show `st.spinner` with bilingual status messages during profile generation.
2. **Live Sync Status Badge**: Show a status indicator in the sidebar (e.g., `🟢 Syncing (Ollama: Llama3)` or `🔴 Idle`).
3. **Contact Selector Optimization**:
   - Cache the contact list using `@st.cache_data`.
   - If the contact list exceeds 500 names, optimize the selectbox or search input to maintain fluid UI performance.
4. **In-View Chat Search**:
   - In the Chat Browser tab, add a `st.text_input` search bar to filter lines in the displayed quarterly log.
   - Ensure the search works for English, Urdu script, and Roman Urdu.

### Testing
- Import a mock data export and verify the progress bar updates smoothly.
- Test UI responsiveness with a simulated list of 1,000 contacts.
- Verify in-view text filtering works correctly with bilingual inputs.

### Documentation
- Update `README.md` with new screenshots or UI flow descriptions.

### Version Update
- Append to `version.md`:
  ```
  [0.6.0] – 2026-06-23
  Added
  - Progress bars for imports and spinners for profile generation.
  - Sidebar status badge indicating sync state and active LLM.
  - High-performance contact selector for large contact lists.
  - Bilingual text search filter inside the Chat Browser.
  ```

---

## Step 6 – Sync Scalability & Dedup Robustness (No Images)
**Criticality**: 🟡 Medium – handles active accounts with high message volume.

### Implementation
1. **Paginated Sync**: Increase sync page size to 50 threads and paginate backwards until the last stored timestamp is reached.
2. **Robust Dedup Keying**: Use Instagram's unique `item_id` as the primary key in `last_sync.json` to prevent duplicates.
3. **Thread Pool Concurrency**: Add `SYNC_MAX_THREADS` to the configuration to control concurrent network operations.
4. **Strict No-Image Enforcement**: Verify that no image assets are fetched, cached, or processed during sync or imports.

### Testing
- Mock paginated Instagram API responses and verify all historical messages are retrieved up to the boundary.
- Verify that messages with duplicate timestamps but different content/IDs are handled correctly.

### Documentation
- Update `README.md` configuration tables with the new sync tuning parameters.

### Version Update
- Append to `version.md`:
  ```
  [0.7.0] – 2026-06-23
  Changed
  - Ingestion pipeline upgraded to use paginated thread sync.
  - Deduplication keying switched to robust item_id tracking.
  Added
  - Concurrent thread-pool controls for background synchronization.
  ```

---

## Step 7 – Project Hygiene & Final Review
**Criticality**: 🟢 Low – ensures codebase maintainability and standards compliance.

### Implementation
1. **Docstring Coverage**: Ensure all public methods across `src/` have clean, bilingual-friendly docstrings.
2. **Project Guidelines**: Create `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` based on project standards.
3. **Dependency Pinning**: Freeze dependencies to exact versions in `requirements.txt`.
4. **Final Version Review**: Verify `version.md` is complete and up to date.

### Testing
- Run the full test suite (`pytest`) to ensure all 12+ tests pass successfully.
- Perform a manual pre-flight check of the completed application.

### Version Update
- Append to `version.md`:
  ```
  [0.8.0] – 2026-06-23
  Added
  - Contributor guidelines and Code of Conduct.
  - Pinned python package dependencies.
  Changed
  - Finalized codebase docstrings.
  - Project documentation audit completed.
  ```