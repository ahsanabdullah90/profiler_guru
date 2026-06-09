## 2026-06-09 - [Profile Persistence & Export]
**Learning:** In Streamlit, AI-generated content (like psychological profiles) should be stored in `st.session_state` to prevent it from disappearing when other widgets trigger a page re-run. Additionally, providing a `st.download_button` for AI reports significantly improves the "portability" of the app's value.
**Action:** Always wrap AI generation results in session state checks and offer an export option for detailed analysis reports.
