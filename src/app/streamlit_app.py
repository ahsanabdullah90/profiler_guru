import streamlit as st
import os
import time
import traceback
import pandas as pd
from datetime import datetime, timezone
from src.engine.instagram_sync import InstagramSync, SyncManager
from src.engine.data_importer import InstagramDataImporter
from src.engine.rag_engine import rag_engine
from src.storage.storage_manager import StorageManager
from src.utils.config import config
from src.utils.ollama_client import ollama_client
from src.utils.logger import logger
from src.engine.metrics_engine import MetricsEngine
from src.utils.task_tracker import task_tracker
from src.engine.settings_manager import settings_manager
from src.engine.llm_dispatcher import llm_dispatcher
from src.engine.report_generator import report_generator

st.set_page_config(page_title="Profile_Guru", layout="wide", page_icon="📸")

def format_relative_time(epoch_ts: float) -> str:
    """Formats an epoch timestamp as a human-readable relative time string."""
    if not epoch_ts:
        return "Never"
    diff = time.time() - epoch_ts
    if diff < 5:
        return "Just now"
    if diff < 60:
        return f"{int(diff)}s ago"
    if diff < 3600:
        return f"{int(diff // 60)}m ago"
    if diff < 86400:
        return f"{int(diff // 3600)}h ago"
    return datetime.fromtimestamp(epoch_ts).strftime("%m-%d %H:%M")

def log_error_to_file(err_traceback: str):
    """Logs tracebacks to a dedicated error file in the app data directory."""
    try:
        log_dir = config.DATA_DIR / "logs"
        os.makedirs(log_dir, exist_ok=True)
        error_file = log_dir / "error.log"
        
        with open(error_file, "a", encoding='utf-8') as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n================ [{timestamp}] UNHANDLED UI EXCEPTION ================\n")
            f.write(err_traceback)
            f.write("\n=====================================================================\n")
    except Exception as e:
        logger.error(f"Failed to write traceback to error.log: {e}")

def check_password():
    """Returns True if the user has authenticated with the correct password."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("🔐 Profile_Guru Portal")
    
    if not config.APP_PASSWORD:
        st.error("🔒 Security Setup Required")
        st.info("The application password is not configured. Please set the `APP_PASSWORD` environment variable in your `.env` file to secure and access Profile_Guru.")
        st.stop()
        return False

    password_input = st.text_input("Enter Access Password", type="password")
    
    if st.button("Authenticate"):
        if password_input == config.APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Access denied.")
            
    return False

@st.cache_data(ttl=10)
def get_contact_names(chats_dir: str) -> list:
    """Caches the list of imported contacts to avoid disk I/O on every UI redraw."""
    if not os.path.exists(chats_dir):
        return []
    return sorted([d for d in os.listdir(chats_dir) if os.path.isdir(os.path.join(chats_dir, d))])

@st.cache_data(ttl=5)
def get_contacts_metadata(chats_dir: str, last_sync_run: dict, _metrics_engine: MetricsEngine) -> dict:
    """Extracts and caches rich metadata for each contact including total messages, last activity, sync times, RAG indexing progress, and connection metrics."""
    metadata = {}
    if not os.path.exists(chats_dir):
        return {}
        
    contacts = sorted([d for d in os.listdir(chats_dir) if os.path.isdir(os.path.join(chats_dir, d))])
    
    for contact in contacts:
        contact_path = os.path.join(chats_dir, contact)
        msg_count = 0
        last_date = "Never"
        last_snippet = "No messages imported yet."
        
        chats_path = os.path.join(contact_path, "Chats")
        if os.path.exists(chats_path):
            files = sorted([f for f in os.listdir(chats_path) if f.endswith(".md")])
            if files:
                # Sum messages across all monthly/quarterly logs
                for file in files:
                    try:
                        with open(os.path.join(chats_path, file), "r", encoding="utf-8") as f:
                            content = f.read()
                            msg_count += content.count("### [")
                    except Exception:
                        pass
                
                # Retrieve last message details from the latest log file
                latest_file = files[-1]
                try:
                    with open(os.path.join(chats_path, latest_file), "r", encoding="utf-8") as f:
                        content = f.read()
                        blocks = [b.strip() for b in content.split("---") if b.strip()]
                        if blocks:
                            last_block = blocks[-1]
                            lines = last_block.split("\n")
                            header = lines[0].strip()
                            body = "\n".join(lines[1:]).strip()
                            
                            # Clean the body preview text
                            if "[Audio]" in body:
                                body = "🎙️ Voice Message"
                            elif "[Imported Audio Transcription" in body or "[Live Audio Transcription" in body:
                                body = "🎙️ Voice: " + body.split("Transcription: ")[-1].strip("]")
                            
                            # Remove markdown markup for clean preview
                            body = body.replace("\n", " ")
                            
                            # Extract timestamp
                            if header.startswith("### ["):
                                closing_bracket_idx = header.find("]")
                                if closing_bracket_idx != -1:
                                    last_date = header[5:closing_bracket_idx][:10]  # Just YYYY-MM-DD
                            
                            last_snippet = body[:35] + "..." if len(body) > 35 else body
                except Exception:
                    pass
                    
        # Query ChromaDB count (fast)
        indexed_chunks = rag_engine.get_indexed_count(contact)
        
        # Get last sync run timestamp
        last_sync_ts = last_sync_run.get(contact, 0)

        # Get connection metrics
        avg_msg = _metrics_engine.get_daily_average(contact, days=7)
                    
        metadata[contact] = {
            "msg_count": msg_count,
            "last_date": last_date,
            "last_snippet": last_snippet,
            "last_sync_ts": last_sync_ts,
            "indexed_chunks": indexed_chunks,
            "avg_msg": avg_msg
        }
    return metadata

@st.cache_data(ttl=10)
def get_global_stats(chats_dir: str) -> dict:
    """Aggregates total statistics across all contacts for the main dashboard."""
    total_contacts = 0
    total_messages = 0
    total_audio = 0
    
    if not os.path.exists(chats_dir):
        return {"contacts": 0, "messages": 0, "audio": 0}
        
    contacts = [d for d in os.listdir(chats_dir) if os.path.isdir(os.path.join(chats_dir, d))]
    total_contacts = len(contacts)
    
    for contact in contacts:
        contact_path = os.path.join(chats_dir, contact)
        
        # Count audio files
        audio_dir = os.path.join(contact_path, "Audio")
        if os.path.exists(audio_dir):
            total_audio += len([f for f in os.listdir(audio_dir) if os.path.isfile(os.path.join(audio_dir, f))])
            
        # Count messages
        chats_path = os.path.join(contact_path, "Chats")
        if os.path.exists(chats_path):
            for file in os.listdir(chats_path):
                if file.endswith(".md"):
                    try:
                        with open(os.path.join(chats_path, file), "r", encoding="utf-8") as f:
                            content = f.read()
                            total_messages += content.count("### [")
                    except Exception:
                        pass
                        
    return {
        "contacts": total_contacts,
        "messages": total_messages,
        "audio": total_audio
    }

def get_contact_avatar_style(contact_name: str, is_selected: bool) -> str:
    """Generates a stable, beautiful, vibrant gradient for each contact based on their name."""
    if is_selected:
        return "linear-gradient(135deg, #007AFF 0%, #0056D6 100%)"
        
    # Curated premium dark-theme gradients
    gradients = [
        "linear-gradient(135deg, #FF5E62 0%, #FF9966 100%)",  # Coral Sunset
        "linear-gradient(135deg, #EF4D7B 0%, #C82B57 100%)",  # Deep Rose
        "linear-gradient(135deg, #11998E 0%, #38EF7D 100%)",  # Mint Green
        "linear-gradient(135deg, #7F00FF 0%, #E100FF 100%)",  # Cosmic Violet
        "linear-gradient(135deg, #00C6FF 0%, #0072FF 100%)",  # Neon Blue
        "linear-gradient(135deg, #F12711 0%, #F5AF19 100%)",  # Golden Flame
        "linear-gradient(135deg, #8E2DE2 0%, #4A00E0 100%)",  # Royal Purple
    ]
    idx = sum(ord(c) for c in contact_name) % len(gradients)
    return gradients[idx]

def evaluate_connection_depth(avg_msgs: float) -> tuple:
    """Returns a tuple of (label, color) indicating connection depth based on weekly average."""
    if avg_msgs >= 15:
        return "Deep Connection 🔥", "#FF9500"
    elif avg_msgs >= 5:
        return "Active Connection 💬", "#32D74B"
    elif avg_msgs >= 1:
        return "Casual Connection ☕", "#007AFF"
    else:
        return "Dormant Connection ❄️", "rgba(255, 255, 255, 0.4)"

def render_message_block(block, chat_name):
    """Parses a raw message block and renders it as a high-fidelity chat bubble with native audio support."""
    block = block.strip()
    if not block:
        return
    
    lines = block.split('\n')
    header = lines[0].strip()
    
    # Identify standard message header format: ### [time_str] sender
    if header.startswith("### ["):
        try:
            closing_bracket_idx = header.find("]")
            if closing_bracket_idx != -1:
                time_str = header[5:closing_bracket_idx]
                sender = header[closing_bracket_idx + 2:].strip()
                
                body_lines = lines[1:]
                body_text = "\n".join(body_lines).strip()
                
                # Scan for voice media download signatures
                audio_path = None
                for line in body_lines:
                    line_strip = line.strip()
                    if line_strip.startswith("[Audio](") and line_strip.endswith(")"):
                        # Extract relative path: ../Audio/filename
                        rel_path = line_strip[8:-1]
                        audio_filename = os.path.basename(rel_path)
                        audio_path = os.path.join(config.CHATS_DIR, chat_name, "Audio", audio_filename)
                        # Strip the raw markdown link from display text
                        body_text = body_text.replace(line_strip, "").strip()
                
                # Align bubble depending on sender identity
                is_self = False
                if config.INSTAGRAM_USERNAME and sender.lower() == config.INSTAGRAM_USERNAME.lower():
                    is_self = True
                
                # Layout properties for high-end aesthetic
                bubble_bg = "rgba(0, 122, 255, 0.12)" if is_self else "rgba(255, 255, 255, 0.03)"
                border_color = "rgba(0, 122, 255, 0.25)" if is_self else "rgba(255, 255, 255, 0.08)"
                alignment = "margin-left: auto; margin-right: 0;" if is_self else "margin-left: 0; margin-right: auto;"
                text_align = "text-align: right;" if is_self else "text-align: left;"
                sender_color = "#007AFF" if is_self else "#32D74B"
                
                st.markdown(f"""
                <div style="background: {bubble_bg}; border: 1px solid {border_color}; border-radius: 12px; padding: 12px 16px; margin: 8px 0; max-width: 80%; {alignment} box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; gap: 20px;">
                        <strong style="color: {sender_color}; font-size: 0.85rem; font-family: 'Inter', sans-serif;">{sender}</strong>
                        <span style="color: rgba(255, 255, 255, 0.4); font-size: 0.75rem; font-family: 'Inter', sans-serif;">{time_str}</span>
                    </div>
                    <div style="color: #E5E2E3; font-size: 0.95rem; line-height: 1.5; white-space: pre-wrap; font-family: 'Inter', sans-serif; {text_align}">{body_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Embed audio player dynamically if local clip exists
                if audio_path and os.path.exists(audio_path):
                    col1, col2 = st.columns([2, 1]) if is_self else st.columns([1, 2])
                    with col1 if not is_self else col2:
                        st.audio(audio_path, format="audio/mp3")
                return
        except Exception as e:
            logger.error(f"Failed to parse message block: {e}")
            
    # Fallback to standard rendering
    st.markdown(block)

def browse_folder() -> str:
    """Opens a native Windows folder selection explorer dialog and returns the selected path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        root.attributes('-topmost', True)  # Bring the dialog to the front
        selected_dir = filedialog.askdirectory(title="Select Instagram Export Folder")
        root.destroy()
        return selected_dir
    except Exception as e:
        logger.error(f"Failed to open folder explorer dialog: {e}")
        return ""

def render_mission_control():
    """Renders the global background task tracker in a beautiful, highly interactive glassmorphic container."""
    active_tasks = task_tracker.get_active_tasks()
    if not active_tasks:
        return
        
    st.markdown("""
    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 15px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
        <h4 style="margin: 0 0 12px 0; color: #FFFFFF; font-size: 0.95rem; font-weight: 600; display: flex; align-items: center; gap: 8px; font-family: 'Inter', sans-serif;">
            <span style="display: inline-block; width: 6px; height: 6px; background-color: #007AFF; border-radius: 50%; box-shadow: 0 0 6px #007AFF; animation: pulse 1.5s infinite;"></span>
            Mission Control - Background Tasks
        </h4>
    </div>
    """, unsafe_allow_html=True)
    
    for task in active_tasks:
        tid = task["id"]
        name = task["name"]
        current = task["current"]
        total = task["total"]
        status = task["status"]
        error = task["error"]
        
        col_info, col_prog, col_btn = st.columns([2, 4, 1])
        
        with col_info:
            if status == "completed":
                status_str = "✅ Completed"
                status_color = "#32D74B"
            elif status == "failed":
                status_str = f"❌ Failed: {error}"
                status_color = "#FF3B30"
            elif status == "cancelling":
                status_str = "⏳ Cancelling..."
                status_color = "#FF9500"
            else:
                status_str = "🏃 Running..."
                status_color = "#007AFF"
                
            st.markdown(f"""
            <div style="font-size: 0.85rem; font-family: 'Inter', sans-serif; line-height: 1.3;">
                <strong>{name}</strong><br>
                <span style="color: {status_color}; font-size: 0.75rem; font-weight: 600;">{status_str}</span>
            </div>
            """, unsafe_allow_html=True)
            
        with col_prog:
            if total > 0:
                pct = min(1.0, current / total)
                st.progress(pct)
                st.markdown(f"<span style='font-size: 0.75rem; color: rgba(255,255,255,0.5); font-family: \"Inter\", sans-serif;'>Processed {current} / {total} files ({int(pct*100)}%)</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='padding-top: 10px;'><span style='font-size: 0.8rem; color: rgba(255,255,255,0.7); font-family: \"Inter\", sans-serif;'>Processed {current} items</span></div>", unsafe_allow_html=True)
                
        with col_btn:
            if status == "running":
                if st.button("Cancel", key=f"cancel_{tid}", use_container_width=True):
                    task_tracker.request_cancel(tid)
                    st.rerun()
            else:
                st.markdown("<div style='padding-top: 5px; text-align: center; color: rgba(255,255,255,0.3); font-size: 0.8rem;'>-</div>", unsafe_allow_html=True)
                
    st.markdown("<hr style='border: none; border-top: 1px solid rgba(255,255,255,0.05); margin-bottom: 25px;'/>", unsafe_allow_html=True)

def render_settings_page():
    import google.generativeai as genai
    
    st.markdown("## ⚙️ Global Settings")
    st.markdown("Configure your AI engine credentials, customize the PDF report layout, and adjust default indexing behaviors.")
    
    # 1. API Credentials Section
    st.markdown("### 🔑 API Credentials & AI Engine")
    
    # Provider selection
    provider_options = ["Google Gemini (Cloud)", "Ollama (Local)"]
    current_provider = settings_manager.get_setting("cloud_provider", "gemini")
    default_provider_idx = 0 if current_provider == "gemini" else 1
    
    selected_provider_label = st.selectbox(
        "Preferred AI Engine",
        provider_options,
        index=default_provider_idx,
        help="Choose the primary AI model provider. Cloud Gemini supports large context windows, while local Ollama is fully private."
    )
    new_provider = "gemini" if "Gemini" in selected_provider_label else "ollama"
    if new_provider != current_provider:
        settings_manager.set_setting("cloud_provider", new_provider)
        
    # Cloud API Key input
    current_key = settings_manager.get_setting("cloud_api_key", "")
    new_key = st.text_input(
        "Google Gemini API Key",
        value=current_key,
        type="password",
        help="Provide your Google AI Studio Gemini API Key. This is required for large personality assessments (>64k tokens)."
    )
    if new_key != current_key:
        settings_manager.set_setting("cloud_api_key", new_key)
        
    # Deep Scan Default
    current_deep_scan = settings_manager.get_setting("deep_scan_default", False)
    new_deep_scan = st.checkbox(
        "Enable Deep Scan by Default",
        value=current_deep_scan,
        help="When enabled, vector search will bypass quick checks and run a thorough search across all message blocks."
    )
    if new_deep_scan != current_deep_scan:
        settings_manager.set_setting("deep_scan_default", new_deep_scan)
        
    # Test Cloud Connection Button
    if st.button("Test Cloud Gemini Connection"):
        if not new_key:
            st.error("Please enter a Google Gemini API Key first.")
        else:
            with st.spinner("Testing connection to Gemini..."):
                try:
                    genai.configure(api_key=new_key)
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content("Hello. Reply with 'Success' if you can hear me.")
                    if response and response.text:
                        st.success("Connection Successful! Cloud Gemini is ready. ✅")
                    else:
                        st.error("Failed to receive a valid response from Gemini.")
                except Exception as e:
                    st.error(f"Connection Failed: {e}")
                    
    st.markdown("---")
    
    # 2. PDF Report Customization Section
    st.markdown("### 📄 PDF Report Layout Settings")
    st.markdown("Toggle which components are included in the downloadable PDF report and customize their layout order.")
    
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        inc_profile = st.checkbox("Include Psychological Analysis", value=settings_manager.get_setting("pdf_include_textual_profile", True))
    with col_t2:
        inc_charts = st.checkbox("Include Visual Trends & Charts", value=settings_manager.get_setting("pdf_include_charts", True))
    with col_t3:
        inc_snippets = st.checkbox("Include Representative Snippets", value=settings_manager.get_setting("pdf_include_raw_snippets", True))
        
    if (inc_profile != settings_manager.get_setting("pdf_include_textual_profile") or
        inc_charts != settings_manager.get_setting("pdf_include_charts") or
        inc_snippets != settings_manager.get_setting("pdf_include_raw_snippets")):
        settings_manager.set_setting("pdf_include_textual_profile", inc_profile)
        settings_manager.set_setting("pdf_include_charts", inc_charts)
        settings_manager.set_setting("pdf_include_raw_snippets", inc_snippets)
        
    # Report Section Reordering Panel (Up/Down Buttons)
    st.markdown("#### ↕️ Report Section Ordering")
    st.markdown("Use the buttons below to change the order of sections in the generated PDF report.")
    
    sections_order = list(settings_manager.get_setting("report_sections_order", ["textual_profile", "charts", "snippets"]))
    
    friendly_names = {
        "textual_profile": "1. Executive Summary & Psychological Analysis",
        "charts": "2. Communication Trends & Sentiment Analysis (Charts)",
        "snippets": "3. Representative Conversation Snippets"
    }
    
    for i, section_name in enumerate(sections_order):
        col_name, col_up, col_down = st.columns([6, 1, 1])
        with col_name:
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 8px 12px; border-radius: 6px; font-weight: 500; font-family: 'Inter', sans-serif;">
                {friendly_names.get(section_name, section_name)}
            </div>
            """, unsafe_allow_html=True)
        with col_up:
            if i > 0:
                if st.button("▲", key=f"up_{section_name}_{i}", use_container_width=True):
                    sections_order[i], sections_order[i-1] = sections_order[i-1], sections_order[i]
                    settings_manager.set_setting("report_sections_order", sections_order)
                    st.rerun()
            else:
                st.markdown("<div style='text-align: center; padding-top: 5px; color: rgba(255,255,255,0.2);'>-</div>", unsafe_allow_html=True)
        with col_down:
            if i < len(sections_order) - 1:
                if st.button("▼", key=f"down_{section_name}_{i}", use_container_width=True):
                    sections_order[i], sections_order[i+1] = sections_order[i+1], sections_order[i]
                    settings_manager.set_setting("report_sections_order", sections_order)
                    st.rerun()
            else:
                st.markdown("<div style='text-align: center; padding-top: 5px; color: rgba(255,255,255,0.2);'>-</div>", unsafe_allow_html=True)
                
    st.markdown("---")
    
    if st.button("Reset Settings to Defaults", type="primary"):
        settings_manager.reset_to_defaults()
        st.success("Settings have been reset to factory defaults! 🔄")
        st.rerun()

def main():
    # 1. Password Gate
    if not check_password():
        return

    # Inject Custom Obsidian Elite styling (glassmorphic dark UI)
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global overrides */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0A0A0C !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: #E5E2E3 !important;
    }
    
    /* Header and Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        color: #FFFFFF !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #111113 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Input fields and Selectboxes */
    div[data-testid="stTextInput"] input, 
    div[data-testid="stSelectbox"] div[role="combobox"], 
    div[data-testid="stNumberInput"] input {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 8px !important;
        color: #FFFFFF !important;
        font-size: 0.95rem !important;
        padding: 8px 12px !important;
    }
    
    div[data-testid="stTextInput"] input:focus, 
    div[data-testid="stSelectbox"] div[role="combobox"]:focus, 
    div[data-testid="stNumberInput"] input:focus {
        border-color: #007AFF !important;
        box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.2) !important;
    }
    
    /* Tabs styling */
    button[data-testid="stTabBarTab"] {
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        color: rgba(255, 255, 255, 0.6) !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.2s ease !important;
    }
    
    button[data-testid="stTabBarTab"][aria-selected="true"] {
        color: #007AFF !important;
        border-bottom: 2px solid #007AFF !important;
    }
    
    button[data-testid="stTabBarTab"]:hover {
        color: #007AFF !important;
    }
    
    /* Expander styling */
    div[data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.01) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 10px !important;
        margin-bottom: 15px !important;
    }
    
    /* Standard Buttons */
    div.stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease-in-out !important;
    }
    
    /* Primary Buttons */
    div.stButton > button[type="primary"], div.stButton > button:active {
        background-color: #007AFF !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3) !important;
    }
    
    div.stButton > button[type="primary"]:hover {
        background-color: #0066D6 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 122, 255, 0.5) !important;
    }
    
    /* Secondary Buttons */
    div.stButton > button:not([type="primary"]) {
        background-color: rgba(255, 255, 255, 0.03) !important;
        color: #E5E2E3 !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    div.stButton > button:not([type="primary"]):hover {
        background-color: rgba(255, 255, 255, 0.06) !important;
        border-color: rgba(255, 255, 255, 0.15) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Progress bar */
    div[data-testid="stProgress"] > div > div > div {
        background-color: #007AFF !important;
    }

    /* Scrollbars */
    ::-webkit-scrollbar {
        width: 6px !important;
        height: 6px !important;
    }
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.01) !important;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.08) !important;
        border-radius: 4px !important;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 122, 255, 0.3) !important;
    }
    
    /* Sync status pulsing animation */
    @keyframes pulse {
        0% { transform: scale(0.9); opacity: 0.6; }
        50% { transform: scale(1.15); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.6; }
    }
    </style>
    """, unsafe_allow_html=True)

    # 2. Global UI Error Boundary
    try:
        # Initialize sync engine and wrapper manager
        if 'sync_engine' not in st.session_state:
            st.session_state.sync_engine = InstagramSync()
        if 'sync_manager' not in st.session_state:
            st.session_state.sync_manager = SyncManager(st.session_state.sync_engine)
        if 'storage_manager' not in st.session_state:
            st.session_state.storage_manager = StorageManager(config.CHATS_DIR)
            
        # Automatic Silent Session Restore on Startup
        if 'logged_in' not in st.session_state:
            session_file = st.session_state.sync_engine.session_path
            if os.path.exists(session_file):
                with st.spinner("Restoring saved Instagram session..."):
                    status, _ = st.session_state.sync_engine.login(None, None)
                    if status == "success":
                        st.session_state.logged_in = True
                    else:
                        st.session_state.logged_in = False
            else:
                st.session_state.logged_in = False

        # Premium Glowing Centered Header
        st.markdown("""
        <div style="text-align: center; padding: 30px 0px 20px 0px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 25px;">
            <h1 style="color: #FFFFFF; font-size: 2.6rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 8px;">📸 <span style="background: linear-gradient(135deg, #007AFF 0%, #32D74B 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Profile_Guru</span></h1>
            <p style="color: rgba(255, 255, 255, 0.6); font-size: 1.05rem; max-width: 600px; margin: 0 auto; line-height: 1.5;">High-fidelity local-first indexing, bilingual voice transcription, and semantic profiling for your Instagram direct messages.</p>
        </div>
        """, unsafe_allow_html=True)

        # 3. Mission Control Top Bar
        render_mission_control()

        sidebar = st.sidebar
        sidebar.header("Navigation & Control")
        
        navigation = sidebar.selectbox("Navigate To", ["📊 Dashboard & Contacts", "⚙️ Global Settings"])
        
        # Privacy & Consent Gate
        sidebar.subheader("🔒 Privacy & Compliance")
        consent_checked = sidebar.checkbox(
            "I agree to cloud processing of chats and voice transcripts (if Gemini is selected).",
            value=st.session_state.get('cloud_consent', False),
            key='cloud_consent'
        )

        # Ollama Auto-detection & LLM Routing Selector
        sidebar.subheader("🤖 AI Engine Configuration")
        
        # Query local Ollama models
        installed_ollama_models = ollama_client.get_installed_models()
        best_local_model = ollama_client.get_best_model(installed_ollama_models)
        
        available_providers = []
        if config.CLOUD_API_KEY or config.GOOGLE_API_KEY:
            available_providers.append("Google Gemini (Cloud)")
        if installed_ollama_models:
            available_providers.append("Ollama (Local)")
            
        if not available_providers:
            sidebar.error("No LLM provider available. Install Ollama locally or set GOOGLE_API_KEY in .env.")
            active_provider = None
        else:
            # Determine default index based on persisted settings
            default_prov = settings_manager.get_setting("cloud_provider", "gemini")
            default_idx = 0
            if default_prov == "ollama" and "Ollama (Local)" in available_providers:
                default_idx = available_providers.index("Ollama (Local)")
            elif default_prov == "gemini" and "Google Gemini (Cloud)" in available_providers:
                default_idx = available_providers.index("Google Gemini (Cloud)")

            selected_provider_label = sidebar.selectbox(
                "Select AI Engine",
                available_providers,
                index=default_idx
            )
            active_provider = "gemini" if "Gemini" in selected_provider_label else "ollama"
            # Sync back to settings manager if changed
            if active_provider != default_prov:
                settings_manager.set_setting("cloud_provider", active_provider)

        selected_ollama_model = None
        if active_provider == "ollama" and installed_ollama_models:
            default_model_idx = installed_ollama_models.index(best_local_model) if best_local_model in installed_ollama_models else 0
            selected_ollama_model = sidebar.selectbox(
                "Active Ollama Model",
                installed_ollama_models,
                index=default_model_idx
            )
            st.session_state.active_model_desc = f"Ollama: {selected_ollama_model}"
        elif active_provider == "gemini":
            st.session_state.active_model_desc = "Gemini 1.5 Flash"
        else:
            st.session_state.active_model_desc = "None"

        # Warn if Gemini selected but consent not given
        if active_provider == "gemini" and not consent_checked:
            sidebar.warning("⚠️ Consent not given. Will automatically fall back to local Ollama if available.")

        sidebar.markdown("---")

        # Instagram Login Section
        if 'two_factor_required' not in st.session_state:
            st.session_state.two_factor_required = False

        with sidebar.expander("Instagram Login", expanded=not st.session_state.logged_in):
            username = st.text_input("Username", value=config.INSTAGRAM_USERNAME or "", placeholder="Enter Instagram Username")
            
            password_placeholder = "•••••••• (Loaded from .env)" if config.INSTAGRAM_PASSWORD else "Enter Instagram Password"
            password = st.text_input("Password", type="password", value="", placeholder=password_placeholder)

            # If 2FA is required, show the code input field
            if st.session_state.two_factor_required:
                st.warning("⚠️ Two-Factor Authentication (2FA) is enabled on this profile.")
                verification_code = st.text_input("Enter 6-Digit 2FA Verification Code", placeholder="e.g., 123456")
                
                if st.button("Submit 2FA Code", type="primary"):
                    if verification_code:
                        with st.spinner("Submitting 2FA verification..."):
                            active_username = username if username else (config.INSTAGRAM_USERNAME or "")
                            active_password = password if password else (config.INSTAGRAM_PASSWORD or "")
                            
                            if not active_username or not active_password:
                                st.error("Please provide both username and password (or configure them in .env).")
                            else:
                                status, info = st.session_state.sync_engine.login(active_username, active_password, verification_code=verification_code)
                                if status == "success":
                                    st.session_state.logged_in = True
                                    st.session_state.two_factor_required = False
                                    st.success("Successfully logged in via 2FA! ✅")
                                    st.rerun()
                                else:
                                    st.error(f"2FA Authentication failed: {info}")
                    else:
                        st.warning("Please enter the verification code.")
            else:
                if st.button("Login"):
                    with st.spinner("Authenticating..."):
                        active_username = username if username else (config.INSTAGRAM_USERNAME or "")
                        active_password = password if password else (config.INSTAGRAM_PASSWORD or "")
                        
                        if not active_username or not active_password:
                            st.error("Please provide both username and password (or configure them in .env).")
                        else:
                            status, info = st.session_state.sync_engine.login(active_username, active_password)
                            if status == "success":
                                st.session_state.logged_in = True
                                st.success("Successfully logged in! ✅")
                                st.rerun()
                            elif status == "2fa_required":
                                st.session_state.two_factor_required = True
                                st.warning("Two-Factor Authentication is required. Enter the verification code above.")
                                st.rerun()
                            elif status == "challenge":
                                st.warning("Challenge required. Check your Instagram app or email.")
                            else:
                                st.error(f"Login failed: {info}")

        # Sync Controls
        if st.session_state.logged_in:
            sync_mgr = st.session_state.sync_manager
            sidebar.success("Account Connected ✅")
            
            if sync_mgr.is_running:
                sidebar.info(f"Background Sync: 🟢 Running ({st.session_state.active_model_desc})")
                if sidebar.button("Stop Background Sync"):
                    sync_mgr.stop()
                    st.rerun()
            else:
                sidebar.info("Background Sync: 🔴 Stopped")
                if sidebar.button("Start Background Sync"):
                    sync_mgr.start()
                    st.rerun()

        # Import Section
        sidebar.header("Historical Import")
        
        if 'import_path_input' not in st.session_state:
            st.session_state.import_path_input = ""
        if 'import_progress' not in st.session_state:
            st.session_state.import_progress = {
                "running": False, "success": False, "error": None, "current": 0, "total": 0, "active_chat": ""
            }

        col_input, col_btn = sidebar.columns([3, 1])
        with col_input:
            import_path = st.text_input(
                "Instagram Export Path", 
                value=st.session_state.import_path_input,
                help="Path to unzipped Instagram data folder"
            )
        with col_btn:
            st.markdown("<div style='padding-top: 25px;'></div>", unsafe_allow_html=True)
            if st.button("📁 Browse"):
                selected_path = browse_folder()
                if selected_path:
                    st.session_state.import_path_input = selected_path
                    st.rerun()

        import_path_clean = import_path.strip()
        preflight_ready = False
        
        if import_path_clean:
            if not os.path.exists(import_path_clean):
                sidebar.error("❌ The specified directory path does not exist. Please check your path and try again.")
            else:
                importer = InstagramDataImporter(st.session_state.storage_manager, sync_engine=st.session_state.sync_engine)
                preflight = importer.preflight_check(import_path_clean)
                if preflight["status"] == "success":
                    stats = preflight["stats"]
                    sidebar.markdown(f"""
                    <div style="background: rgba(0, 122, 255, 0.04); border: 1px solid rgba(0, 122, 255, 0.15); border-radius: 8px; padding: 12px; margin: 10px 0;">
                        <span style="color: #FFFFFF; font-size: 0.85rem; font-weight: 600; font-family: 'Inter', sans-serif;">📊 Export Structure Verified</span><br>
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.7); line-height: 1.4; font-family: 'Inter', sans-serif;">
                            • Chat Threads: <strong>{stats['total_threads']}</strong><br>
                            • Message Files: <strong>{stats['total_json_files']}</strong>
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    preflight_ready = True
                else:
                    sidebar.error(f"⚠️ {preflight['message']}")

        if preflight_ready and not st.session_state.import_progress["running"]:
            if sidebar.button("Import & Index Data", type="primary"):
                st.session_state.import_progress = {
                    "running": True, "success": False, "error": None, "current": 0, "total": 0, "active_chat": "Initializing..."
                }
                
                # Launch import in a separate background thread to prevent UI freezing
                import threading
                importer = InstagramDataImporter(st.session_state.storage_manager, sync_engine=st.session_state.sync_engine)
                progress_state = st.session_state.import_progress
                
                def bg_import():
                    try:
                        def progress_cb(current, total, active_chat):
                            progress_state["current"] = current
                            progress_state["total"] = total
                            progress_state["active_chat"] = active_chat
                        
                        res = importer.import_from_json(import_path_clean, progress_callback=progress_cb)
                        if res:
                            progress_state["success"] = True
                        else:
                            progress_state["error"] = "Import failed or cancelled."
                    except Exception as ex:
                        progress_state["error"] = str(ex)
                        logger.error(f"Background import thread crashed: {ex}")
                    finally:
                        progress_state["running"] = False
                
                t = threading.Thread(target=bg_import, daemon=True)
                t.start()
                st.rerun()

        # Render active import progress indicators in the sidebar
        progress_state = st.session_state.import_progress
        if progress_state["running"]:
            current = progress_state["current"]
            total = progress_state["total"]
            active_chat = progress_state["active_chat"]
            
            sidebar.markdown("### 📥 Ingesting Historical Data...")
            if total > 0:
                percent = int((current / total) * 100)
                sidebar.progress(percent)
                sidebar.markdown(f"""
                <div style="font-size: 0.85rem; color: rgba(255, 255, 255, 0.8); line-height: 1.5; margin-top: 5px; font-family: 'Inter', sans-serif;">
                    • Progress: <strong>{current} / {total}</strong> folders ({percent}%)<br>
                    • Current Chat: <span style="color: #007AFF; font-weight: 600;">{active_chat}</span>
                </div>
                """, unsafe_allow_html=True)
            else:
                sidebar.info("Analyzing directories and initializing...")
            
            import time
            time.sleep(1.0)
            st.rerun()
        elif progress_state["success"]:
            sidebar.success("Import completed successfully! 🎉")
            st.session_state.import_progress = {
                "running": False, "success": False, "error": None, "current": 0, "total": 0, "active_chat": ""
            }
            st.cache_data.clear()  # Refresh contact selector cache
            st.rerun()
        elif progress_state["error"]:
            sidebar.error(f"❌ Import failed: {progress_state['error']}")
            st.session_state.import_progress = {
                "running": False, "success": False, "error": None, "current": 0, "total": 0, "active_chat": ""
            }

        # Initialize session state for selected contact
        if 'selected_contact' not in st.session_state:
            st.session_state.selected_contact = None

        # Fetch contacts metadata
        contacts_metadata = get_contacts_metadata(
            str(config.CHATS_DIR), 
            st.session_state.sync_engine.last_sync_run,
            st.session_state.sync_engine.metrics_engine
        )
        
        # Defensive check to handle Streamlit session persistence for active_syncs
        if not hasattr(st.session_state.sync_engine, 'active_syncs'):
            st.session_state.sync_engine.active_syncs = set()
        active_syncs = st.session_state.sync_engine.active_syncs

        if navigation == "⚙️ Global Settings":
            render_settings_page()
            return

        # Create dual-pane workspace layout
        col_list, col_main = st.columns([1, 2], gap="large")

        with col_list:
            st.markdown("<h3 style='color: #FFFFFF; font-size: 1.25rem; font-weight: 700; margin-bottom: 10px; font-family: \"Inter\", sans-serif;'>📁 Contacts Grid</h3>", unsafe_allow_html=True)
            
            # Contact Search Box
            search_query = st.text_input("Search contacts...", value="", placeholder="🔍 Search contacts...", label_visibility="collapsed")
            
            # Sorting selector
            sort_by = st.selectbox(
                "Sort Contacts By", 
                ["Messaging Volume (Weekly)", "Recent Activity", "Alphabetical"]
            )
            
            # Live Syncing Indicator
            if active_syncs:
                st.markdown(f"""
                <div style="background: rgba(50, 215, 75, 0.06); border: 1px solid rgba(50, 215, 75, 0.2); border-radius: 8px; padding: 8px 12px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; width: 8px; height: 8px; background-color: #32D74B; border-radius: 50%; box-shadow: 0 0 8px #32D74B; animation: pulse 1.5s infinite;"></span>
                    <span style="color: #32D74B; font-size: 0.8rem; font-weight: 600; font-family: 'Inter', sans-serif;">{len(active_syncs)} syncing in background</span>
                </div>
                """, unsafe_allow_html=True)

            # Filter and Sort contacts
            filtered_contacts = [c for c in contacts_metadata.keys() if not search_query or search_query.lower() in c.lower()]

            if sort_by == "Alphabetical":
                filtered_contacts.sort()
            elif sort_by == "Recent Activity":
                # Sort by last sync run or last modified log
                filtered_contacts.sort(key=lambda c: contacts_metadata[c]["last_sync_ts"], reverse=True)
            else:  # Messaging Volume (Weekly)
                # Sort by average weekly messages
                filtered_contacts.sort(key=lambda c: contacts_metadata[c]["avg_msg"], reverse=True)

            if filtered_contacts:
                for contact in filtered_contacts:
                    info = contacts_metadata[contact]
                    msg_count = info["msg_count"]
                    last_date = info["last_date"]
                    last_snippet = info["last_snippet"]
                    avg_msg = info["avg_msg"]
                    
                    # Avatar Initials & Gradient Background
                    initials = contact[:2].upper() if len(contact) >= 2 else contact[0].upper()
                    
                    is_selected = st.session_state.selected_contact == contact
                    is_syncing = contact in active_syncs
                    
                    avatar_bg = get_contact_avatar_style(contact, is_selected)
                    
                    # Styled Card background and border based on selection
                    if is_selected:
                        card_bg = "rgba(0, 122, 255, 0.08)"
                        card_border = "rgba(0, 122, 255, 0.3)"
                        card_shadow = "0 4px 12px rgba(0, 122, 255, 0.15)"
                    else:
                        card_bg = "rgba(255, 255, 255, 0.01)"
                        card_border = "rgba(255, 255, 255, 0.05)"
                        card_shadow = "none"
                        
                    badge_bg = "rgba(0, 122, 255, 0.1)" if is_selected else "rgba(255, 255, 255, 0.03)"
                    badge_border = "rgba(0, 122, 255, 0.2)" if is_selected else "rgba(255, 255, 255, 0.08)"
                    badge_color = "#007AFF" if is_selected else "rgba(255, 255, 255, 0.6)"
                    
                    sync_dot = ""
                    if is_syncing:
                        sync_dot = '<span style="display: inline-block; width: 8px; height: 8px; background-color: #32D74B; border-radius: 50%; box-shadow: 0 0 8px #32D74B; margin-left: 6px; animation: pulse 1.5s infinite;"></span>'

                    # RAG progress
                    indexed_chunks = info["indexed_chunks"]
                    rag_progress = min(100, int((indexed_chunks / msg_count) * 100)) if msg_count > 0 else 0
                    
                    # Connection Depth metrics evaluation
                    depth_label, depth_color = evaluate_connection_depth(avg_msg)
                    
                    # Compute status
                    last_sync_ts = info["last_sync_ts"]
                    if is_syncing:
                        sync_status_color = "#32D74B"
                        sync_status_icon = "🟢"
                        sync_status_text = "Syncing..."
                    elif last_sync_ts > 0:
                        sync_status_color = "#007AFF"
                        sync_status_icon = "🔄"
                        sync_status_text = f"Synced {format_relative_time(last_sync_ts)}"
                    else:
                        sync_status_color = "rgba(255, 255, 255, 0.4)"
                        sync_status_icon = "📂"
                        sync_status_text = "Imported"
                        
                    if rag_progress == 100:
                        rag_status_color = "#007AFF" if is_selected else "rgba(255, 255, 255, 0.8)"
                        rag_badge_bg = "rgba(0, 122, 255, 0.06)"
                        rag_badge_border = "rgba(0, 122, 255, 0.15)"
                    else:
                        rag_status_color = "#FF9500"
                        rag_badge_bg = "rgba(255, 149, 0, 0.06)"
                        rag_badge_border = "rgba(255, 149, 0, 0.15)"

                    st.markdown(f"""
                    <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px; padding: 12px; margin-bottom: 4px; box-shadow: {card_shadow}; display: flex; flex-direction: column;">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 32px; height: 32px; border-radius: 50%; background: {avatar_bg}; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #FFFFFF; font-size: 0.85rem; font-family: 'Inter', sans-serif;">
                                    {initials}
                                </div>
                                <strong style="color: #FFFFFF; font-size: 0.9rem; display: flex; align-items: center; font-family: 'Inter', sans-serif;">{contact} {sync_dot}</strong>
                            </div>
                            <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.4); font-family: 'Inter', sans-serif;">{last_date}</span>
                        </div>
                        
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; gap: 10px;">
                            <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px; font-family: 'Inter', sans-serif;">
                                {last_snippet}
                            </span>
                            <span style="background: {badge_bg}; color: {badge_color}; font-size: 0.65rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; border: 1px solid {badge_border}; white-space: nowrap; font-family: 'Inter', sans-serif;">
                                {msg_count} msgs
                            </span>
                        </div>
                        
                        <!-- Connection Depth Indicator Badge -->
                        <div style="margin-top: 6px; display: flex; align-items: center; gap: 6px;">
                            <span style="color: {depth_color}; font-size: 0.7rem; font-weight: 600; font-family: 'Inter', sans-serif; background: rgba(255,255,255,0.02); padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.04);">
                                {depth_label} ({avg_msg:.1f}/day)
                            </span>
                        </div>

                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.03); gap: 10px;">
                            <span style="font-size: 0.7rem; color: {sync_status_color}; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 4px;">
                                {sync_status_icon} {sync_status_text}
                            </span>
                            <span style="font-size: 0.7rem; color: {rag_status_color}; font-family: 'Inter', sans-serif; display: flex; align-items: center; gap: 4px; background: {rag_badge_bg}; padding: 1px 6px; border-radius: 6px; border: 1px solid {rag_badge_border}; font-weight: 500;">
                                🤖 {rag_progress}% ({indexed_chunks})
                            </span>
                        </div>
                    </div>
                    """.replace("\n", " ").strip(), unsafe_allow_html=True)
                    
                    btn_label = "Active Conversation" if is_selected else f"Open {contact}"
                    btn_type = "primary" if is_selected else "secondary"
                    if st.button(btn_label, key=f"sel_{contact}", use_container_width=True, type=btn_type):
                        st.session_state.selected_contact = contact
                        st.rerun()
            else:
                st.markdown("<span style='font-size: 0.85rem; color: rgba(255, 255, 255, 0.4); font-style: italic;'>No contacts found.</span>", unsafe_allow_html=True)

        with col_main:
            if st.session_state.selected_contact:
                sel_contact = st.session_state.selected_contact
                info = contacts_metadata.get(sel_contact, {"msg_count": 0, "last_date": "Never", "last_snippet": "", "last_sync_ts": 0, "indexed_chunks": 0, "avg_msg": 0, "avg_audio": 0})
                initials = sel_contact[:2].upper() if len(sel_contact) >= 2 else sel_contact[0].upper()
                
                # Calculate sync status and RAG details
                last_sync_ts = info.get("last_sync_ts", 0)
                indexed_chunks = info.get("indexed_chunks", 0)
                rag_progress = min(100, int((indexed_chunks / info["msg_count"]) * 100)) if info["msg_count"] > 0 else 0
                
                last_sync_text = f"Synced {format_relative_time(last_sync_ts)}" if last_sync_ts > 0 else "Imported"
                if sel_contact in active_syncs:
                    last_sync_text = "Syncing in background..."

                # Active Contact Header
                avatar_gradient = get_contact_avatar_style(sel_contact, False)
                col_hdr_left, col_hdr_right = st.columns([4, 1])
                with col_hdr_left:
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; gap: 15px; background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 12px 20px; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);">
                        <div style="width: 42px; height: 42px; border-radius: 50%; background: {avatar_gradient}; display: flex; align-items: center; justify-content: center; font-weight: 700; color: #FFFFFF; font-size: 1.1rem; font-family: 'Inter', sans-serif;">
                            {initials}
                        </div>
                        <div>
                            <h2 style="margin: 0; font-size: 1.25rem; color: #FFFFFF; font-weight: 700; font-family: 'Inter', sans-serif;">{sel_contact}</h2>
                            <span style="font-size: 0.75rem; color: rgba(255, 255, 255, 0.5); font-family: 'Inter', sans-serif;">Messages: <strong>{info['msg_count']}</strong> | Status: <strong>{last_sync_text}</strong> | RAG Index: <strong>{rag_progress}% ({indexed_chunks} chunks)</strong></span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_hdr_right:
                    st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
                    if st.button("❌ Close Chat", use_container_width=True, key="close_chat_btn"):
                        st.session_state.selected_contact = None
                        st.rerun()

                # Tabbed Details Workspace (Added Connection Analytics tab)
                tab_chat, tab_profile, tab_analytics, tab_rag = st.tabs([
                    "💬 Conversation History", 
                    "👤 Personality Assessment", 
                    "📊 Connection Analytics",
                    "🤖 Ask AI (RAG)"
                ])
                
                with tab_chat:
                    contact_path = os.path.join(config.CHATS_DIR, sel_contact, "Chats")
                    if os.path.exists(contact_path):
                        files = sorted(os.listdir(contact_path), reverse=True)
                        if files:
                            sel_file = st.selectbox("Monthly Log", files, key=f"file_sel_{sel_contact}")
                            
                            with open(os.path.join(contact_path, sel_file), "r", encoding='utf-8') as f:
                                file_content = f.read()
                                
                            search_filter = st.text_input("🔍 Search within messages (English / Urdu)", placeholder="Type keywords...", key=f"search_{sel_contact}")
                            
                            message_blocks = [b.strip() for b in file_content.split("---") if b.strip()]
                            message_blocks.reverse()
                            
                            if search_filter:
                                matches = [b for b in message_blocks if search_filter.lower() in b.lower()]
                                if matches:
                                    st.success(f"Found **{len(matches)}** matching messages:")
                                    for match in matches:
                                        render_message_block(match, sel_contact)
                                else:
                                    st.warning("No messages matched your search query.")
                            else:
                                messages_per_page = 50
                                total_messages = len(message_blocks)
                                
                                if total_messages > messages_per_page:
                                    num_pages = (total_messages + messages_per_page - 1) // messages_per_page
                                    col_page, col_info = st.columns([1, 3])
                                    with col_page:
                                        page = st.number_input("Page", min_value=1, max_value=num_pages, value=1, step=1, key=f"page_sel_{sel_contact}")
                                    with col_info:
                                        start_idx = (page - 1) * messages_per_page
                                        end_idx = min(start_idx + messages_per_page, total_messages)
                                        st.markdown(f"""
                                        <div style="padding-top: 25px; color: rgba(255, 255, 255, 0.6); font-size: 0.9rem; font-family: 'Inter', sans-serif;">
                                            Showing messages <strong>{start_idx + 1}</strong> to <strong>{end_idx}</strong> of <strong>{total_messages}</strong>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    visible_blocks = message_blocks[start_idx:end_idx]
                                else:
                                    visible_blocks = message_blocks
                                    
                                for block in visible_blocks:
                                    render_message_block(block, sel_contact)
                        else:
                            st.write("No message logs found for this contact.")
                    else:
                        st.write("Storage structure not found.")
                        
                with tab_profile:
                    st.markdown("### 👤 Personality Assessment")
                    st.markdown(f"Generate and review deep psychological profile assessments for **{sel_contact}** using historical message patterns.")
                    
                    # Date Range Selection
                    chats_dir_path = Path(config.CHATS_DIR) / sel_contact / "Chats"
                    if chats_dir_path.exists():
                        available_months = sorted([f[:-3] for f in os.listdir(chats_dir_path) if f.endswith(".md")])
                    else:
                        available_months = []
                        
                    if not available_months:
                        st.warning("No conversation logs found for this contact. Import some data to run assessments!")
                    else:
                        # Month Dropdowns & Presets
                        col_start, col_end = st.columns(2)
                        
                        # Initialize session state for start/end month selection
                        if f'start_month_{sel_contact}' not in st.session_state:
                            st.session_state[f'start_month_{sel_contact}'] = available_months[0]
                        if f'end_month_{sel_contact}' not in st.session_state:
                            st.session_state[f'end_month_{sel_contact}'] = available_months[-1]
                            
                        with col_start:
                            start_month = st.selectbox(
                                "Start Month", 
                                available_months, 
                                index=available_months.index(st.session_state[f'start_month_{sel_contact}']),
                                key=f'start_sel_{sel_contact}'
                            )
                            st.session_state[f'start_month_{sel_contact}'] = start_month
                            
                        with col_end:
                            end_month = st.selectbox(
                                "End Month", 
                                available_months, 
                                index=available_months.index(st.session_state[f'end_month_{sel_contact}']),
                                key=f'end_sel_{sel_contact}'
                            )
                            st.session_state[f'end_month_{sel_contact}'] = end_month
                            
                        # Presets Buttons
                        col_p1, col_p2, col_p3 = st.columns(3)
                        with col_p1:
                            if st.button("Last Month Preset", key=f"pres_last_{sel_contact}", use_container_width=True):
                                st.session_state[f'start_month_{sel_contact}'] = available_months[-1]
                                st.session_state[f'end_month_{sel_contact}'] = available_months[-1]
                                st.rerun()
                        with col_p2:
                            if st.button("Last 3 Months Preset", key=f"pres_last3_{sel_contact}", use_container_width=True):
                                st.session_state[f'end_month_{sel_contact}'] = available_months[-1]
                                idx = max(0, len(available_months) - 3)
                                st.session_state[f'start_month_{sel_contact}'] = available_months[idx]
                                st.rerun()
                        with col_p3:
                            if st.button("Custom Range Preset", key=f"pres_custom_{sel_contact}", use_container_width=True):
                                st.session_state[f'start_month_{sel_contact}'] = available_months[0]
                                st.session_state[f'end_month_{sel_contact}'] = available_months[-1]
                                st.rerun()
                                
                        # Fetch the snippets for the selected range to estimate tokens
                        range_snippets = rag_engine.fetch_markdown_snippets(sel_contact, start_month, end_month)
                        token_estimate = rag_engine.estimate_token_count(range_snippets)
                        
                        # Display Token Estimate Metric
                        col_tok_metric, col_tok_info = st.columns([1, 2])
                        with col_tok_metric:
                            st.metric("Estimated Prompt Tokens", f"{token_estimate:,}")
                        with col_tok_info:
                            if token_estimate > config.PERSONA_ASSESS_MAX_LOCAL_TOKENS:
                                st.markdown(f"""
                                <div style="background: rgba(255, 149, 0, 0.08); border: 1px solid rgba(255, 149, 0, 0.2); border-radius: 8px; padding: 10px 15px; font-size: 0.85rem; line-height: 1.4; font-family: 'Inter', sans-serif;">
                                    ⚠️ <b>Context limit exceeded for local model ({config.PERSONA_ASSESS_MAX_LOCAL_TOKENS:,} tokens).</b><br/>
                                    This assessment requires <b>Google Gemini (Cloud)</b> to process the full text.
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown(f"""
                                <div style="background: rgba(50, 215, 75, 0.08); border: 1px solid rgba(50, 215, 75, 0.2); border-radius: 8px; padding: 10px 15px; font-size: 0.85rem; line-height: 1.4; font-family: 'Inter', sans-serif;">
                                    ✅ <b>Within local model context limits.</b><br/>
                                    This assessment can be run fully privately on your local Ollama instance (<b>{selected_ollama_model or config.OLLAMA_MODEL}</b>).
                                </div>
                                """, unsafe_allow_html=True)
                                
                        # Additional controls
                        col_c1, col_c2 = st.columns(2)
                        with col_c1:
                            deep_scan = st.checkbox(
                                "Thorough Deep Scan", 
                                value=settings_manager.get_setting("deep_scan_default", False),
                                key=f"deep_scan_assess_{sel_contact}",
                                help="Bypasses caching and forces a fresh query of all available conversation logs."
                            )
                        with col_c2:
                            force_cloud = st.checkbox(
                                "Force Cloud Gemini", 
                                value=False,
                                key=f"force_cloud_{sel_contact}",
                                help="Force the assessment to use Cloud Gemini even if it fits within local model limits."
                            )
                            
                        # Run Assessment Button
                        if st.button("Generate Detailed Personality Assessment", type="primary", key=f"run_assess_{sel_contact}"):
                            if not range_snippets:
                                st.error("No message snippets found in the selected date range.")
                            else:
                                with st.spinner(f"Analyzing conversation patterns for {sel_contact} from {start_month} to {end_month}..."):
                                    prompt = f"""
Analyze the following Instagram direct message logs for the contact '{sel_contact}'.
Provide a detailed psychological and behavioral assessment. Highlight their linguistic habits, communication style, emotional temperament, sentiments towards the user, and psychological profile.

CHAT LOGS:
{range_snippets}
"""
                                    profile_text = llm_dispatcher.dispatch(
                                        prompt=prompt,
                                        token_budget=token_estimate,
                                        force_cloud=force_cloud,
                                        provider=active_provider,
                                        ollama_model=selected_ollama_model,
                                        user_consent=consent_checked
                                    )
                                    st.session_state[f"assess_result_{sel_contact}"] = profile_text
                                    st.session_state[f"assess_range_{sel_contact}"] = (start_month, end_month)
                                    # Clear old compiled PDF to avoid serving wrong version
                                    if f"pdf_bytes_{sel_contact}" in st.session_state:
                                        del st.session_state[f"pdf_bytes_{sel_contact}"]
                                    st.rerun()
                                    
                        # If an assessment has been run, show it
                        if f"assess_result_{sel_contact}" in st.session_state:
                            profile_text = st.session_state[f"assess_result_{sel_contact}"]
                            saved_start, saved_end = st.session_state[f"assess_range_{sel_contact}"]
                            
                            st.markdown(f"""
                            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 25px; margin-top: 20px; box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.01);">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 10px;">
                                    <span style="display: inline-block; width: 8px; height: 8px; background-color: #007AFF; border-radius: 50%; box-shadow: 0 0 8px #007AFF;"></span>
                                    <h3 style="color: #FFFFFF; font-size: 1.1rem; margin: 0; font-weight: 600; font-family: 'Inter', sans-serif;">Psychological Assessment Report ({saved_start} to {saved_end})</h3>
                                </div>
                                <div style="color: #E5E2E3; font-size: 0.95rem; line-height: 1.6; font-family: 'Inter', sans-serif;">
                            """, unsafe_allow_html=True)
                            st.markdown(profile_text)
                            st.markdown("</div></div>", unsafe_allow_html=True)
                            
                            # PDF Generation & Download Trigger
                            st.markdown("### 📥 Download PDF Report")
                            st.markdown("Export this assessment, along with messaging statistics, charts, and raw message snippets, as a premium PDF report.")
                            
                            if st.button("Compile PDF Report", key=f"compile_pdf_{sel_contact}", type="primary"):
                                with st.spinner("Generating PDF report (assembling pages, charts, and tables)..."):
                                    export_dir = Path(config.EXPORTS_DIR)
                                    os.makedirs(export_dir, exist_ok=True)
                                    pdf_filename = f"{sel_contact}_personality_report.pdf"
                                    pdf_path = export_dir / pdf_filename
                                    
                                    # Generate using our report_generator
                                    report_generator.create_assessment_pdf(
                                        contact=sel_contact,
                                        start_month=saved_start,
                                        end_month=saved_end,
                                        content=profile_text,
                                        settings=settings_manager.settings,
                                        out_path=pdf_path
                                    )
                                    
                                    try:
                                        with open(pdf_path, "rb") as f:
                                            pdf_bytes = f.read()
                                        st.session_state[f"pdf_bytes_{sel_contact}"] = pdf_bytes
                                        st.session_state[f"pdf_filename_{sel_contact}"] = pdf_filename
                                        st.success("PDF Compiled successfully! Click the button below to download.")
                                    except Exception as e:
                                        st.error(f"Failed to read compiled PDF: {e}")
                                        
                            # Render the download button if bytes are available
                            if f"pdf_bytes_{sel_contact}" in st.session_state:
                                st.download_button(
                                    label="📥 Download Compiled PDF Report",
                                    data=st.session_state[f"pdf_bytes_{sel_contact}"],
                                    file_name=st.session_state[f"pdf_filename_{sel_contact}"],
                                    mime="application/pdf",
                                    key=f"dl_pdf_btn_{sel_contact}",
                                    use_container_width=True
                                )

                with tab_analytics:
                    st.markdown("### 📊 Connection Analytics & Metrics")
                    st.markdown("Quantify connection depth using daily/weekly message volumes and communication patterns.")
                    
                    # Display metrics in a beautiful grid
                    metrics_engine = st.session_state.sync_engine.metrics_engine
                    avg_msg_weekly = metrics_engine.get_daily_average(sel_contact, days=7)
                    avg_msg_monthly = metrics_engine.get_daily_average(sel_contact, days=30)
                    depth_label, depth_color = evaluate_connection_depth(avg_msg_weekly)
                    
                    col_m1, col_m2, col_m3 = st.columns(3)
                    with col_m1:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 15px; text-align: center;">
                            <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5); font-family: 'Inter', sans-serif;">Connection Status</span><br>
                            <strong style="font-size: 1.15rem; color: {depth_color}; font-weight: 700; font-family: 'Inter', sans-serif; display: block; margin-top: 6px;">{depth_label}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_m2:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 15px; text-align: center;">
                            <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5); font-family: 'Inter', sans-serif;">Weekly Daily Avg</span><br>
                            <strong style="font-size: 1.5rem; color: #007AFF; font-weight: 800; font-family: 'Inter', sans-serif; display: block; margin-top: 4px;">{avg_msg_weekly:.2f}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_m3:
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; padding: 15px; text-align: center;">
                            <span style="font-size: 0.8rem; color: rgba(255,255,255,0.5); font-family: 'Inter', sans-serif;">Monthly Daily Avg</span><br>
                            <strong style="font-size: 1.5rem; color: #32D74B; font-weight: 800; font-family: 'Inter', sans-serif; display: block; margin-top: 4px;">{avg_msg_monthly:.2f}</strong>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
                    
                    # Fetch daily history from database
                    stats_14d = metrics_engine.get_daily_stats(sel_contact, days=14)
                    
                    if stats_14d:
                        st.markdown("#### 📈 14-Day Activity Trend")
                        # Format into a DataFrame for st.line_chart
                        dates = [s[0] for s in stats_14d]
                        msgs = [s[1] for s in stats_14d]
                        
                        df = pd.DataFrame({
                            "Messages": msgs
                        }, index=dates)
                        
                        st.line_chart(df)
                    else:
                        st.info("No daily activity stats recorded yet. Sync messages to start collecting daily activity data!")

                    st.markdown("---")
                    st.markdown("#### 📥 Export Connection Metrics")
                    st.markdown("Download all metrics in the database for connection-depth analysis.")
                    
                    export_fmt = st.radio("Export Format", ["CSV", "JSON"], horizontal=True, key=f"fmt_radio_{sel_contact}")
                    if st.button("Generate Export", type="primary", key=f"exp_btn_{sel_contact}"):
                        file_path = st.session_state.sync_engine.metrics_engine.export_metrics(fmt=export_fmt.lower())
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                export_data = f.read()
                            st.download_button(
                                label=f"Click to Download {export_fmt}",
                                data=export_data,
                                file_name=f"connection_metrics_{sel_contact}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.{export_fmt.lower()}",
                                mime="text/csv" if export_fmt == "CSV" else "application/json",
                                key=f"dl_btn_{sel_contact}"
                            )
                        except Exception as e:
                            st.error(f"Failed to export: {e}")
                            
                with tab_rag:
                    st.markdown("### 🤖 Contact AI Assistant")
                    st.markdown(f"Ask any question about your conversation logs with **{sel_contact}**.")
                    
                    # Date range selection
                    chats_dir_path = Path(config.CHATS_DIR) / sel_contact / "Chats"
                    if chats_dir_path.exists():
                        available_months = sorted([f[:-3] for f in os.listdir(chats_dir_path) if f.endswith(".md")])
                    else:
                        available_months = []
                        
                    if available_months:
                        use_full_history = st.checkbox("Use Full Conversation History", value=True, key=f"rag_full_hist_{sel_contact}")
                        
                        start_month = None
                        end_month = None
                        
                        if not use_full_history:
                            col_start, col_end = st.columns(2)
                            with col_start:
                                start_month = st.selectbox(
                                    "Query Start Month", 
                                    available_months, 
                                    index=0,
                                    key=f"rag_start_{sel_contact}"
                                )
                            with col_end:
                                end_month = st.selectbox(
                                    "Query End Month", 
                                    available_months, 
                                    index=len(available_months)-1,
                                    key=f"rag_end_{sel_contact}"
                                )
                                
                        # Deep Scan preference
                        deep_scan_ai = st.checkbox(
                            "Deep Scan (Bypass vector database index, query markdown directly)", 
                            value=settings_manager.get_setting("deep_scan_default", False),
                            key=f"deep_scan_ai_{sel_contact}",
                            help="Force the AI to search the raw markdown logs directly for maximum completeness."
                        )
                        
                        query = st.text_input("Ask a question about this contact's history:", placeholder="e.g., What did we discuss about our project?", key=f"rag_query_{sel_contact}")
                        
                        if st.button("Query Contact Logs", type="primary", key=f"rag_btn_{sel_contact}"):
                            if query:
                                with st.spinner(f"Querying history and vector index for {sel_contact}..."):
                                    # 1. Retrieve markdown snippets
                                    markdown_snippets = rag_engine.fetch_markdown_snippets(sel_contact, start_month, end_month)
                                    
                                    # 2. Query ChromaDB for top-20 chunks if not deep scan and collection exists
                                    vector_chunks = []
                                    if not deep_scan_ai:
                                        try:
                                            # Filter query by chat_name
                                            where_filter = {"chat_name": sel_contact}
                                            results = rag_engine.collection.query(
                                                query_texts=[query],
                                                n_results=20,
                                                where=where_filter
                                            )
                                            if results and results.get('documents') and results['documents'][0]:
                                                vector_chunks = results['documents'][0]
                                        except Exception as e:
                                            logger.error(f"Vector search failed: {e}")
                                            
                                    # 3. Concatenate sources
                                    context_parts = []
                                    if markdown_snippets:
                                        context_parts.append(f"MARKDOWN LOG SNIPPETS (Selected Range):\n{markdown_snippets}")
                                    if vector_chunks:
                                        context_parts.append("SEMANTICALLY RETRIEVED VECTOR CHUNKS:\n" + "\n---\n".join(vector_chunks))
                                        
                                    context = "\n\n=========================================\n\n".join(context_parts)
                                    
                                    # Capping context length depending on LLM selection
                                    max_chars = 300000 if active_provider == "gemini" else 15000
                                    if len(context) > max_chars:
                                        context = context[:max_chars] + "\n\n[Context truncated for token limits...]"
                                        
                                    token_estimate = rag_engine.estimate_token_count(context)
                                    
                                    prompt = f"""
You are an AI assistant analyzing Instagram DMs.
Use the following chat history context (comprising raw markdown logs and semantic search snippets) to answer the user's question accurately.
If the answer is not contained in the context, synthesize the best possible response from the snippets or state that it is not explicitly mentioned.

CONTEXT:
{context}

USER QUESTION:
{query}

ANSWER:
"""
                                    # Dispatch to LLM using dispatcher
                                    response = llm_dispatcher.dispatch(
                                        prompt=prompt,
                                        token_budget=token_estimate,
                                        force_cloud=False,
                                        provider=active_provider,
                                        ollama_model=selected_ollama_model,
                                        user_consent=consent_checked
                                    )
                                    
                                    st.markdown(f"""
                                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; margin-top: 15px; box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.01);">
                                        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 10px;">
                                            <span style="display: inline-block; width: 8px; height: 8px; background-color: #32D74B; border-radius: 50%; box-shadow: 0 0 8px #32D74B;"></span>
                                            <strong style="color: #FFFFFF; font-size: 1.0rem; font-family: 'Inter', sans-serif;">AI Synthesis (Contact: {sel_contact})</strong>
                                        </div>
                                        <div style="color: #E5E2E3; font-size: 0.95rem; line-height: 1.6; font-family: 'Inter', sans-serif; white-space: pre-wrap;">
                                    """, unsafe_allow_html=True)
                                    st.markdown(response)
                                    st.markdown("</div></div>", unsafe_allow_html=True)
                            else:
                                st.warning("Please enter a question.")
                    else:
                        st.warning("No conversation logs found. Import some data to start chatting with the AI!")
            else:
                # Welcome Dashboard
                st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(0, 122, 255, 0.1) 0%, rgba(50, 215, 75, 0.1) 100%); border: 1px solid rgba(255, 255, 255, 0.04); border-radius: 16px; padding: 26px 30px; margin-bottom: 30px; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);">
                    <h2 style="color: #FFFFFF; font-size: 1.7rem; font-weight: 800; margin: 0 0 8px 0; letter-spacing: -0.02em; font-family: 'Inter', sans-serif;">👋 Welcome to Profile_Guru</h2>
                    <p style="color: rgba(255, 255, 255, 0.65); font-size: 0.95rem; margin: 0; line-height: 1.5; font-family: 'Inter', sans-serif;">Select a contact from the sidebar list to view their quarterly conversation history, play voice messages, generate psychological profiles, or search their chat logs.</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Fetch statistics
                stats = get_global_stats(str(config.CHATS_DIR))
                
                # Statistics Grid
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);">
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.45); font-weight: 500; font-family: 'Inter', sans-serif;">Indexed Messages</span><br>
                        <strong style="font-size: 1.6rem; color: #007AFF; font-weight: 800; font-family: 'Inter', sans-serif; display: block; margin-top: 4px;">{stats['messages']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                with col_stat2:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);">
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.45); font-weight: 500; font-family: 'Inter', sans-serif;">Synced Contacts</span><br>
                        <strong style="font-size: 1.6rem; color: #32D74B; font-weight: 800; font-family: 'Inter', sans-serif; display: block; margin-top: 4px;">{stats['contacts']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                with col_stat3:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);">
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.45); font-weight: 500; font-family: 'Inter', sans-serif;">Voice Transcripts</span><br>
                        <strong style="font-size: 1.6rem; color: #FF9500; font-weight: 800; font-family: 'Inter', sans-serif; display: block; margin-top: 4px;">{stats['audio']}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                with col_stat4:
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 10px; text-align: center; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);">
                        <span style="font-size: 0.8rem; color: rgba(255, 255, 255, 0.45); font-weight: 500; font-family: 'Inter', sans-serif;">Active Engine</span><br>
                        <strong style="font-size: 0.85rem; color: #FFFFFF; font-weight: 700; font-family: 'Inter', sans-serif; display: block; margin-top: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{st.session_state.active_model_desc}</strong>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
                
                # Global Search Card
                st.markdown("### 🔍 Global Intelligence Search (RAG)")
                st.markdown("Perform semantic search and synthesize answers across your entire database of contacts.")
                global_query = st.text_input("Ask a question across all contacts:", placeholder="e.g., What did we talk about last Christmas?", key="global_query_input")
                if st.button("Search All Contacts", type="primary", key="global_search_btn"):
                    if global_query:
                        with st.spinner("Searching entire vector database..."):
                            response = rag_engine.query(
                                global_query, 
                                chat_filter=None,
                                provider=active_provider,
                                ollama_model=selected_ollama_model,
                                user_consent=consent_checked
                            )
                            st.markdown(f"""
                            <div style="background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; margin-top: 15px; box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.01);">
                                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 10px;">
                                    <span style="display: inline-block; width: 8px; height: 8px; background-color: #007AFF; border-radius: 50%; box-shadow: 0 0 8px #007AFF;"></span>
                                    <strong style="color: #FFFFFF; font-size: 1.0rem; font-family: 'Inter', sans-serif;">Global AI Synthesis</strong>
                                </div>
                                <div style="color: #E5E2E3; font-size: 0.95rem; line-height: 1.6; font-family: 'Inter', sans-serif; white-space: pre-wrap;">{response}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.warning("Please enter a question.")

                # System Ingestion State / Background sync status
                st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
                st.markdown("### 🔄 Global System Metrics Export")
                st.markdown("Export all connection-depth metrics for psychological profiling across all contacts.")
                
                col_exp_1, col_exp_2 = st.columns([3, 1])
                with col_exp_1:
                    global_export_fmt = st.radio("Export Format", ["CSV", "JSON"], horizontal=True, key="global_fmt_radio")
                with col_exp_2:
                    st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
                    if st.button("Export All Metrics", type="primary", key="global_export_btn", use_container_width=True):
                        file_path = st.session_state.sync_engine.metrics_engine.export_metrics(fmt=global_export_fmt.lower())
                        try:
                            with open(file_path, "r", encoding="utf-8") as f:
                                export_data = f.read()
                            st.download_button(
                                label=f"Download All ({global_export_fmt})",
                                data=export_data,
                                file_name=f"all_connection_metrics_{datetime.now(timezone.utc).strftime('%Y%m%d')}.{global_export_fmt.lower()}",
                                mime="text/csv" if global_export_fmt == "CSV" else "application/json",
                                key="global_dl_btn"
                            )
                        except Exception as e:
                            st.error(f"Failed to export global metrics: {e}")

                # Live Sync Status Monitor Card
                st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)
                st.markdown("### 🔄 Live Sync Status Monitor")
                
                sync_mgr = st.session_state.sync_manager
                if sync_mgr.is_running:
                    status_color = "#32D74B"
                    status_text = "Background synchronization is running in a separate daemon thread."
                    badge_status = "ACTIVE"
                else:
                    status_color = "rgba(255, 255, 255, 0.3)"
                    status_text = "Background synchronization is stopped."
                    badge_status = "STOPPED"
                    
                st.markdown(f"""
                <div style="background: rgba(255, 255, 255, 0.01); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 20px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.15); display: flex; flex-direction: column;">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); padding-bottom: 10px;">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <span style="display: inline-block; width: 8px; height: 8px; background-color: {status_color}; border-radius: 50%; box-shadow: 0 0 8px {status_color};"></span>
                            <strong style="color: #FFFFFF; font-size: 1.0rem; font-family: 'Inter', sans-serif;">System Ingestion State</strong>
                        </div>
                        <span style="background: rgba(255, 255, 255, 0.05); color: {status_color}; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 6px; border: 1px solid rgba(255, 255, 255, 0.08); font-family: 'Inter', sans-serif;">{badge_status}</span>
                    </div>
                    <p style="color: rgba(255, 255, 255, 0.7); font-size: 0.9rem; margin-top: 0; line-height: 1.4; font-family: 'Inter', sans-serif;">{status_text}</p>
                """, unsafe_allow_html=True)
                
                if active_syncs:
                    st.markdown("<span style='font-size: 0.85rem; color: #FFFFFF; font-weight: 600; display: block; margin-bottom: 8px; font-family: \"Inter\", sans-serif;'>Actively syncing contacts:</span>", unsafe_allow_html=True)
                    for ac in sorted(active_syncs):
                        st.markdown(f"""
                        <div style="background: rgba(50, 215, 75, 0.05); border: 1px solid rgba(50, 215, 75, 0.15); border-radius: 8px; padding: 8px 12px; margin-bottom: 6px; display: flex; align-items: center; justify-content: space-between;">
                            <span style="color: #E5E2E3; font-size: 0.85rem; font-family: 'Inter', sans-serif;">👤 {ac}</span>
                            <span style="color: #32D74B; font-size: 0.75rem; font-weight: 600; display: flex; align-items: center; gap: 6px; font-family: 'Inter', sans-serif;">
                                <span style="display: inline-block; width: 6px; height: 6px; background-color: #32D74B; border-radius: 50%; box-shadow: 0 0 6px #32D74B; animation: pulse 1.5s infinite;"></span>
                                processing thread...
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    if sync_mgr.is_running:
                        st.markdown("<span style='font-size: 0.85rem; color: rgba(255, 255, 255, 0.5); font-style: italic; font-family: \"Inter\", sans-serif;'>Idle - Waiting for next sync cycle...</span>", unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='font-size: 0.85rem; color: rgba(255, 255, 255, 0.5); font-style: italic; font-family: \"Inter\", sans-serif;'>Sync manager is inactive. Start background sync in the sidebar.</span>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

    except Exception as e:
        # Log unhandled exceptions to error.log
        err_traceback = traceback.format_exc()
        log_error_to_file(err_traceback)
        
        # Display elegant error card to the user
        st.error("🚨 An unexpected error occurred in the interface layout.")
        st.info("This event has been logged gracefully. Please check the logs under your App Data directory.")
        with st.expander("Show Diagnostics"):
            st.code(err_traceback, language="python")

if __name__ == "__main__":
    main()
