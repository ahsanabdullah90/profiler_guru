## 2026-06-15 - Streamlit Tab Persistence & Accessibility

**Learning:** Streamlit components inside tabs are subject to the same re-run logic as the rest of the page. Without explicit session state persistence, AI-generated content (like psychological profiles) is lost when the user switches tabs or interacts with other widgets. Additionally, many Streamlit widgets lack inherent accessible descriptions for screen readers or hover guidance unless the `help` parameter is utilized.

**Action:**
1. Always persist generated analytical reports in `st.session_state` using a unique key per contact/subject.
2. Clear or update the persisted state when the primary selection (e.g., contact dropdown) changes to prevent displaying stale data.
3. Consistently use the `help` parameter on buttons and inputs to provide contextual guidance and improve accessibility.
