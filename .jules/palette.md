## 2026-06-02 - Profile Persistence in Streamlit
**Learning:** Streamlit re-runs the entire script upon user interaction. AI-generated reports must be stored in `st.session_state` to prevent data loss when interacting with related widgets (e.g., a download button).
**Action:** Always check if complex or expensive AI outputs should be persisted in `session_state` to maintain a seamless UX.
