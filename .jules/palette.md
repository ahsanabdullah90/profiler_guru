## 2026-06-04 - [Streamlit State Persistence]
**Learning:** In Streamlit apps, AI-generated content (like search results or analysis reports) should be persisted in `st.session_state` to prevent data loss when other UI interactions trigger a page re-run.
**Action:** Always check if computationally expensive or AI-generated results need to be stored in `session_state` for a smoother user experience.

## 2026-06-04 - [Accessibility with Help Tooltips]
**Learning:** Using the `help` parameter in Streamlit widgets is a low-effort, high-impact way to provide contextual guidance and improve accessibility for complex inputs.
**Action:** Add `help` tooltips to any form field or button whose function might not be immediately obvious to a first-time user.
