## 2024-06-11 - [Streamlit State Persistence & Export]
**Learning:** In Streamlit, AI-generated reports or complex analysis results disappear during app re-runs (triggered by other widget interactions) unless stored in `st.session_state`. Additionally, users benefit from direct export options for AI content.
**Action:** Always persist AI outputs in `st.session_state` and provide a `st.download_button` for report portability.
