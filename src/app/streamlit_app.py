import streamlit as st
import os
from src.engine.instagram_sync import InstagramSync
from src.engine.data_importer import InstagramDataImporter
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config

st.set_page_config(page_title="InstaSync AI", layout="wide", page_icon="📸")

def main():
    st.title("📸 InstaSync AI: DM Analysis & Profiler")

    if 'sync_engine' not in st.session_state:
        st.session_state.sync_engine = InstagramSync()
    if 'storage_manager' not in st.session_state:
        st.session_state.storage_manager = StorageManager(config.CHATS_DIR)
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False

    sidebar = st.sidebar
    sidebar.header("Settings & Sync")

    # Login Section
    with sidebar.expander("Instagram Login", expanded=not st.session_state.logged_in):
        username = st.text_input("Username", value=config.INSTAGRAM_USERNAME or "")
        password = st.text_input("Password", type="password", value=config.INSTAGRAM_PASSWORD or "")

        if st.button("Login"):
            with st.spinner("Authenticating..."):
                status, info = st.session_state.sync_engine.login(username, password)
                if status == "success":
                    st.session_state.logged_in = True
                    st.success("Successfully logged in!")
                elif status == "challenge":
                    st.warning("Challenge required. Check your Instagram app or email.")
                    # In a real app, we'd add an input for the code here
                else:
                    st.error(f"Login failed: {info}")

    # Sync Controls
    if st.session_state.logged_in:
        sidebar.success("Account Connected ✅")
        if sidebar.button("Start Background Sync"):
            st.session_state.sync_engine.start()
            st.sidebar.info("Background sync running...")

        if sidebar.button("Stop Background Sync"):
            st.session_state.sync_engine.stop()
            st.sidebar.info("Sync stopped.")

    # Import Section
    sidebar.header("Historical Import")
    import_path = sidebar.text_input("Instagram Export Path", help="Path to unzipped Instagram data folder")
    if sidebar.button("Import & Index Data"):
        importer = InstagramDataImporter(st.session_state.storage_manager)
        with st.spinner("Processing media and indexing..."):
            if importer.import_from_json(import_path):
                st.success("Import successful!")
            else:
                st.error("Import failed. See logs.")

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 AI Search (RAG)", "👤 Personality Profiler", "📁 Chat Browser"])

    with tab1:
        st.header("Search Your Chat History")
        query = st.text_input("What would you like to know?", placeholder="e.g., What did we talk about last Christmas?")

        existing_chats = ["None"]
        if os.path.exists(config.CHATS_DIR):
            existing_chats += [d for d in os.listdir(config.CHATS_DIR) if os.path.isdir(os.path.join(config.CHATS_DIR, d))]

        chat_filter = st.selectbox("Specific Contact Filter", existing_chats)

        if st.button("Search AI", type="primary"):
            if query:
                filter_val = None if chat_filter == "None" else chat_filter
                with st.spinner("Searching..."):
                    response = rag_engine.query(query, chat_filter=filter_val)
                    st.write("**AI Analysis:**")
                    st.info(response)
            else:
                st.warning("Please enter a query.")

    with tab2:
        st.header("Psychological Assessment")
        if len(existing_chats) > 1:
            contact_to_profile = st.selectbox("Select Contact", existing_chats[1:])
            if st.button("Generate Psychological Profile"):
                with st.spinner(f"Analyzing communication patterns for {contact_to_profile}..."):
                    profile = rag_engine.analyze_profile(contact_to_profile)
                    st.write(f"### Profile for {contact_to_profile}")
                    st.markdown(profile)

                    st.download_button(
                        label="📥 Download Profile (MD)",
                        data=profile,
                        file_name=f"profile_{contact_to_profile.replace(' ', '_')}.md",
                        mime="text/markdown",
                        help="Save this psychological assessment for your records."
                    )
        else:
            st.info("Import some chats first to use the profiler.")

        with tab3:
            st.header("Local File Browser")
            if len(existing_chats) > 1:
                sel_browser = st.selectbox("View Contact Data", existing_chats[1:], key="browser_sel")
                contact_path = os.path.join(config.CHATS_DIR, sel_browser, "Chats")
                if os.path.exists(contact_path):
                    files = sorted(os.listdir(contact_path), reverse=True)
                    if files:
                        sel_file = st.selectbox("Quarterly Log", files)
                        with open(os.path.join(contact_path, sel_file), "r", encoding='utf-8') as f:
                            st.markdown(f.read())
                    else:
                        st.write("No message logs found for this contact.")
                else:
                    st.write("Storage structure not found.")
            else:
                st.info("No data available to browse.")

if __name__ == "__main__":
    main()
