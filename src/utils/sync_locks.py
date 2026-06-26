"""
sync_locks.py — Process-level singleton locks for background thread synchronization.

These locks are module-level singletons. They survive web server request lifecycles 
and provide stable synchronization between the API endpoints and background daemon threads.
"""
import threading

# Guards background data-import operations and progress state mutations
IMPORT_LOCK = threading.Lock()
