## 2025-05-15 - [Persistence and Export for Streamlit AI Reports]
**Learning:** In Streamlit, AI-generated content (like psychological profiles) is lost on widget interaction unless explicitly stored in `st.session_state`. Providing a `st.download_button` significantly improves the utility of one-off AI analyses.
**Action:** Always use `st.session_state` to buffer AI outputs and provide an export option (Markdown/PDF) for text-heavy reports.

## 2025-05-15 - [Accessibility through Tooltips]
**Learning:** Streamlit's `help` parameter is a low-effort, high-impact way to add ARIA-compatible tooltips to almost all interactive widgets.
**Action:** Use `help` on all buttons and inputs to provide contextual guidance without cluttering the UI.
