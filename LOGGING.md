# Profile_Guru Logging Documentation

Profile_Guru implements a structured, rotating file logging system. All log outputs are located inside the application's secure data directory.

---

## Log Locations

On Windows systems, logs are written to:
`%LOCALAPPDATA%/Profile_Guru/logs/`

On macOS/Linux systems, logs are written to:
`~/.profile_guru/logs/`

### 1. Application Log (`app.log`)
Contains operational details, status updates, network API responses, and background synchronization task outputs.
* **Rotation**: Rotates when the file reaches **5 MB**.
* **Backups**: Keeps up to **2 historical backups** (`app.log.1`, `app.log.2`).

---

## Log Formatting

Logs follow a standardized prefix format:
`[TIMESTAMP] - [LOGGER_NAME] - [LOG_LEVEL] - [MESSAGE]`

Example entry:
`2026-06-23 20:21:00 - Profile_Guru - INFO - Background sync manager started.`

---

## Troubleshooting via Logs

1. **Local LLM Connection Issues**: If local searches fail, check `app.log` for connection timeouts to `http://localhost:11434`.
2. **Instagram Session Expirations**: If synchronization pauses, search for `Session expired, attempting fresh login` or specific authentication challenge reports in `app.log`.
3. **Unexpected UI Freezes**: View `app.log` for precise traceback details.
