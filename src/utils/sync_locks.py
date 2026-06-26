"""
sync_locks.py — Process-level singleton locks for background thread synchronization.

These locks are module-level singletons. Unlike threading.Lock() stored in
st.session_state (which is recreated on every Streamlit script rerun), these
instances survive all reruns and provide stable synchronization between the
Streamlit UI thread and background daemon threads.
"""
import threading

# Guards background data-import operations and progress state mutations
IMPORT_LOCK = threading.Lock()
