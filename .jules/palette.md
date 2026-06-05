# Palette's Journal - Critical UX/Accessibility Learnings

## 2025-05-14 - Initial Setup
**Learning:** Streamlit apps often lose state on re-run, which can be frustrating for users after waiting for long-running AI operations.
**Action:** Always persist AI-generated results in `st.session_state` to ensure a smooth, persistent experience.
