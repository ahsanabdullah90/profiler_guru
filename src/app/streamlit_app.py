import streamlit as st
import os
from src.engine.instagram_sync import InstagramSync
from src.engine.data_importer import InstagramDataImporter
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config

st.set_page_config(page_title="InstaSync AI", layout="wide")

def main():
    st.title("📸 InstaSync AI: DM Analysis & Profiler")

    if 'sync_engine' not in st.session_state:
        st.session_state.sync_engine = InstagramSync()
    if 'storage_manager' not in st.session_state:
        st.session_state.storage_manager = StorageManager(config.CHATS_DIR)

    sidebar = st.sidebar
    sidebar.header("Settings & Sync")

    # Login Section
    with sidebar.expander("Instagram Login"):
        username = st.text_input("Username", value=config.INSTAGRAM_USERNAME or "")
        password = st.text_input("Password", type="password", value=config.INSTAGRAM_PASSWORD or "")
        if st.button("Login"):
            success = st.session_state.sync_engine.login(username, password)
            if success:
                st.success("Logged in!")
            else:
                st.error("Login failed.")

    # Sync Controls
    if sidebar.button("Start Background Sync"):
        st.session_state.sync_engine.start()
        st.sidebar.info("Background sync started.")

    if sidebar.button("Stop Background Sync"):
        st.session_state.sync_engine.stop()
        st.sidebar.info("Background sync stopped.")

    # Import Section
    sidebar.header("Historical Import")
    import_path = sidebar.text_input("Instagram Export Path")
    if sidebar.button("Import Data"):
        importer = InstagramDataImporter(st.session_state.storage_manager)
        with st.spinner("Importing and Indexing..."):
            if importer.import_from_json(import_path):
                st.success("Import successful!")
            else:
                st.error("Import failed. Check logs.")

    # Main Tabs
    tab1, tab2, tab3 = st.tabs(["🔍 Search & RAG", "👤 Profiler", "📁 Chat Browser"])

    with tab1:
        st.header("Search Conversations")
        query = st.text_input("Ask a question about your chats")
        chat_filter = st.selectbox("Filter by contact (Optional)", ["None"] + os.listdir(config.CHATS_DIR))

        if st.button("Query"):
            filter_val = None if chat_filter == "None" else chat_filter
            response = rag_engine.query(query, chat_filter=filter_val)
            st.write("**AI Response:**")
            st.info(response)

    with tab2:
        st.header("Psychological Profiler")
        contact_to_profile = st.selectbox("Select a contact to analyze", os.listdir(config.CHATS_DIR))
        if st.button("Generate Profile"):
            with st.spinner(f"Analyzing {contact_to_profile}..."):
                profile = rag_engine.analyze_profile(contact_to_profile)
                st.write(f"**Profile for {contact_to_profile}:**")
                st.markdown(profile)

    with tab3:
        st.header("Local Chat Files")
        contacts = os.listdir(config.CHATS_DIR)
        selected_contact = st.selectbox("View Contact", contacts, key="browser")
        if selected_contact:
            contact_path = os.path.join(config.CHATS_DIR, selected_contact, "Chats")
            if os.path.exists(contact_path):
                files = os.listdir(contact_path)
                selected_file = st.selectbox("Quarter File", files)
                if selected_file:
                    with open(os.path.join(contact_path, selected_file), "r", encoding='utf-8') as f:
                        st.markdown(f.read())

if __name__ == "__main__":
    main()
