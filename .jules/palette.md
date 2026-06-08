## 2026-06-08 - Persisting AI-Generated Reports in Streamlit

**Learning:** AI-generated content (like psychological profiles) is lost in Streamlit when the user interacts with other widgets (e.g., download buttons or filters) because interaction triggers a full page re-run.

**Action:** Always persist AI-generated analysis in `st.session_state` and check for its presence before rendering, ensuring the user can download or review the content without re-triggering expensive AI calls.
