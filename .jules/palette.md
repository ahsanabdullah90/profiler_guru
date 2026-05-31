## 2026-05-31 - [Streamlit Session Persistence & Accessibility]
**Learning:** In Streamlit apps, AI-generated content (like psychological profiles) must be persisted in `st.session_state` to prevent data loss when subsequent user actions trigger a page re-run. Additionally, using the `help` parameter in action buttons significantly improves accessibility and user guidance.
**Action:** Always check for potential data loss on re-run and use `st.session_state` for results. Proactively add `help` tooltips to major interactive elements.
