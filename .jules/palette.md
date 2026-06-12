## 2025-05-15 - [Persistence and Export in Streamlit]
**Learning:** Streamlit apps often lose state on user interaction (like button clicks or selectbox changes), which is frustrating when waiting for long-running AI generations like psychological profiles. Using `st.session_state` to persist results and providing a `st.download_button` significantly improves the utility and perceived reliability of the tool.
**Action:** Always persist AI-generated analysis in `st.session_state` and provide an export option (Markdown/JSON) for data portability.
