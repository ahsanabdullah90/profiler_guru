## 2026-06-01 - [Streamlit Session State Persistence]
**Learning:** AI-generated content in Streamlit (like psychological profiles) can be lost during page re-runs caused by user interactions (e.g., clicking a different tab or adjusting a slider). Explicitly persisting this content in `st.session_state` is critical for a smooth UX.
**Action:** Always check if complex or expensive AI outputs need to be stored in `st.session_state` and restored upon re-render, especially when using interactive widgets that trigger app re-execution.
