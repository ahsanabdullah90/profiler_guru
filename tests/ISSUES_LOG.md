# Issues Log - Testing Phase

During the implementation of the automated test suite, the following issues/bugs were identified:

1. **StorageManager: Invalid Timestamp Handling**
   - **File:** `src/storage/storage_manager.py`
   - **Method:** `save_message` / `get_quarter_filename`
   - **Issue:** If an invalid timestamp (e.g., a string) is passed to `save_message`, it bypasses the `datetime.fromtimestamp` conversion but is still passed to `get_quarter_filename`, where it causes an `AttributeError: 'str' object has no attribute 'month'`.
   - **Impact:** Crash when processing malformed data.
   - **Status:** Logged.

2. **RAGEngine: Hardcoded Database Path**
   - **File:** `src/engine/rag_engine.py`
   - **Issue:** The database path `chroma_db` is hardcoded in `__init__`, making it difficult to point to a temporary test database without patching the instance.
   - **Impact:** Testing isolation is harder to achieve.
   - **Status:** Mitigated in tests via patching.

3. **MediaProcessor: Missing Dependency Handling**
   - **File:** `src/engine/media_processor.py`
   - **Issue:** Loading Whisper models and Gemini configuration relies heavily on environment variables and presence of GPU. Failures in `setup_whisper` are logged but the class remains in a partially initialized state.
   - **Status:** Logged.

4. **MediaProcessor: Missing 'media_processor' object**
   - **File:** `src/engine/media_processor.py`
   - **Issue:** Several modules (`data_importer.py`, `instagram_sync.py`) attempt to import `media_processor` from `src.engine.media_processor`, but the module only contains functions and no such object exists.
   - **Impact:** `ImportError` preventing tests and synchronization from running.
   - **Status:** Identified during logger testing phase.
