## 2026-06-06 - [Streamlit Session State Persistence]
**Learning:** In Streamlit apps, AI-generated content (like analysis reports or psychological profiles) should be stored in `st.session_state`. This ensures the content remains visible when subsequent user interactions (like switching tabs or clicking other buttons) trigger a page re-run.
**Action:** Always check if critical AI output needs to survive re-runs and implement `st.session_state` persistence for those components.
