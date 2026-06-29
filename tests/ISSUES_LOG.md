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

1. **WebSocket heartbeat-reconnect bug**: `lib/ws.ts:191-195` calls `this.close()` which sets `destroyed=true` and prevents `scheduleReconnect` from firing. Should call `ws.close()` instead.
2. **Toast container missing `role="alert"`**: `Toast.tsx` error notifications are invisible to screen readers.
3. **`config.last_user_activity` removed**: Was read by instagram_sync.py but never written. Now removed entirely.
4. **`MetricsEngine` read methods not lock-protected**: Concurrent readers in WAL mode are generally safe, but Python sqlite3 shared connection is not thread-safe for cursor operations.
