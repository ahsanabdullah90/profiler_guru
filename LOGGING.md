# InstaSync AI Logging Documentation

InstaSync AI implements a structured, rotating file logging system alongside a dedicated UI exception tracker. All log outputs are located inside the application's secure data directory.

---

## Log Locations

On Windows systems, logs are written to:
`%LOCALAPPDATA%/InstaSync/logs/`

On macOS/Linux systems, logs are written to:
`~/.instasync/logs/`

### 1. Application Log (`app.log`)
Contains operational details, status updates, network API responses, and background synchronization task outputs.
* **Rotation**: Rotates when the file reaches **5 MB**.
* **Backups**: Keeps up to **2 historical backups** (`app.log.1`, `app.log.2`).

### 2. UI Exception Log (`error.log`)
Captures full tracebacks and diagnostics for any unhandled exceptions that occur within the Streamlit interface. This prevents the server from crashing and allows for fast troubleshooting.

---

## Log Formatting

Logs follow a standardized prefix format:
`[TIMESTAMP] - [LOGGER_NAME] - [LOG_LEVEL] - [MESSAGE]`

Example entry:
`2026-06-23 20:21:00 - InstaSync - INFO - Background sync manager started.`

---

## Troubleshooting via Logs

1. **Local LLM Connection Issues**: If local searches fail, check `app.log` for connection timeouts to `http://localhost:11434`.
2. **Instagram Session Expirations**: If synchronization pauses, search for `Session expired, attempting fresh login` or specific authentication challenge reports in `app.log`.
3. **Unexpected UI Freezes**: View `error.log` for precise traceback details.
