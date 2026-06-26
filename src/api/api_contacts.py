import os
import html
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from src.utils.config import config
from src.utils.logger import logger
from src.engine.rag_engine import rag_engine
from src.api.state import sync_engine
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param
from src.utils.redis_client import cache_get, cache_set, cache_delete, cache_delete_pattern

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])

def evaluate_connection_depth(avg_msgs: float) -> tuple:
    if avg_msgs >= 15:
        return "Deep Connection 🔥", "#FF9500"
    elif avg_msgs >= 5:
        return "Active Connection 💬", "#32D74B"
    elif avg_msgs >= 1:
        return "Casual Connection ☕", "#007AFF"
    else:
        return "Dormant Connection ❄️", "rgba(255, 255, 255, 0.4)"

@router.get("")
def get_contacts(current_user: dict = Depends(get_current_user)):
    try:
        # Try cache first
        cached = cache_get("contacts:list:all")
        if cached is not None:
            return cached

        metrics_engine = sync_engine.metrics_engine
        db_meta = metrics_engine.get_all_contact_metadata_with_counts()
        
        if not db_meta:
            return []
            
        contacts_list = list(db_meta.keys())
        
        # Bulk fetch averages and vector index counts
        all_daily_averages = {}
        try:
            all_daily_averages = metrics_engine.get_all_daily_averages(days=7)
        except Exception as e:
            logger.error(f"Failed to bulk-fetch daily averages: {e}")
            
        all_indexed_counts = {}
        try:
            all_indexed_counts = rag_engine.get_all_indexed_counts(contacts=contacts_list)
        except Exception as e:
            logger.error(f"Failed to bulk-fetch indexed counts: {e}")
            
        result = []
        for contact, info in db_meta.items():
            msg_count = info.get("message_count", 0)
            last_date = info.get("last_date", "Never")
            last_snippet = info.get("last_snippet", "No messages imported yet.")
            avg_msg = all_daily_averages.get(contact, 0.0)
            indexed_chunks = all_indexed_counts.get(contact, 0)
            
            rag_progress = min(100, int((indexed_chunks / msg_count) * 100)) if msg_count > 0 else 0
            depth_label, depth_color = evaluate_connection_depth(avg_msg)
            
            result.append({
                "name": contact,
                "msg_count": msg_count,
                "last_date": last_date,
                "last_snippet": last_snippet,
                "avg_msg": avg_msg,
                "indexed_chunks": indexed_chunks,
                "rag_progress": rag_progress,
                "depth_label": depth_label,
                "depth_color": depth_color
            })
            
        # Sort contacts from latest to oldest activity by default
        # "Never" dates are sorted to the bottom
        def sort_key(c):
            d = c["last_date"]
            if d == "Never" or not d:
                return "0000-00-00"
            return d
            
        result.sort(key=sort_key, reverse=True)
        cache_set("contacts:list:all", result)
        return result
    except Exception as e:
        logger.error(f"Error getting contacts list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/months")
def get_contact_months(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    contact_path = Path(config.CHATS_DIR) / name / "Chats"
    if not contact_path.exists():
        return []
    try:
        files = sorted(
            [f for f in os.listdir(contact_path) if f.endswith(".md")],
            reverse=True
        )
        return files
    except Exception as e:
        logger.error(f"Error listing months for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/messages/{month}")
def get_contact_messages(name: str, month: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    validate_safe_param(month, "month")
    file_path = Path(config.CHATS_DIR) / name / "Chats" / month
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Monthly log file not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        message_blocks = [b.strip() for b in content.split("---") if b.strip()]
        # We display them oldest first or latest first? The React UI should handle ordering, 
        # but chronologically (oldest at the top, scrolling down to latest) is standard.
        # The raw file stores them chronologically (oldest first, appending to the bottom).
        # So we return them in chronological order.
        
        parsed_messages = []
        for idx, block in enumerate(message_blocks):
            lines = block.split("\n")
            header = lines[0].strip()
            
            if header.startswith("### ["):
                closing_bracket_idx = header.find("]")
                if closing_bracket_idx != -1:
                    time_str = header[5:closing_bracket_idx]
                    sender = header[closing_bracket_idx + 2:].strip()
                    
                    body_lines = lines[1:]
                    body_text = "\n".join(body_lines).strip()
                    
                    # Check for voice message
                    audio_url = None
                    for line in body_lines:
                        line_strip = line.strip()
                        if line_strip.startswith("[Audio](") and line_strip.endswith(")"):
                            rel_path = line_strip[8:-1]
                            audio_filename = os.path.basename(rel_path)
                            audio_local_path = Path(config.CHATS_DIR) / name / "Audio" / audio_filename
                            if audio_local_path.exists():
                                # Static path exposed on /static/audio/{name}/{filename}
                                audio_url = f"/static/audio/{name}/{audio_filename}"
                            body_text = body_text.replace(line_strip, "").strip()
                            
                    is_self = False
                    if config.INSTAGRAM_USERNAME and sender.lower() == config.INSTAGRAM_USERNAME.lower():
                        is_self = True
                        
                    parsed_messages.append({
                        "id": f"{month}_{idx}",
                        "sender": html.escape(sender),
                        "time": html.escape(time_str),
                        "text": html.escape(body_text),
                        "audio_url": audio_url,
                        "is_self": is_self
                    })
            else:
                # Fallback for non-standard blocks
                parsed_messages.append({
                    "id": f"{month}_{idx}",
                    "sender": "System",
                    "time": "",
                    "text": html.escape(block),
                    "audio_url": None,
                    "is_self": False
                })
                
        return parsed_messages
    except Exception as e:
        logger.error(f"Error reading messages for {name} ({month}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/analytics")
def get_contact_analytics(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        # Try cache first
        cache_key = f"analytics:{name}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        metrics_engine = sync_engine.metrics_engine
        
        # 1. Weekly vs Monthly Daily Average
        avg_msg_weekly = metrics_engine.get_daily_average(name, days=7)
        avg_msg_monthly = metrics_engine.get_daily_average(name, days=30)
        
        # 2. Connection Depth
        depth_label, depth_color = evaluate_connection_depth(avg_msg_weekly)
        
        # 3. 14-day timeline activity stats
        stats_14d = metrics_engine.get_daily_stats(name, days=14)
        timeline_data = []
        if stats_14d:
            for row in stats_14d:
                timeline_data.append({
                    "date": row[0],
                    "messages": row[1]
                })
                
        # 4. Audio ratio
        audio_dir = Path(config.CHATS_DIR) / name / "Audio"
        audio_count = 0
        if audio_dir.exists():
            audio_count = len([f for f in os.listdir(audio_dir) if (audio_dir / f).is_file()])
            
        db_meta = metrics_engine.get_all_contact_metadata_with_counts()
        total_messages = db_meta.get(name, {}).get("message_count", 0)
        
        audio_ratio = (audio_count / total_messages * 100) if total_messages > 0 else 0
        
        result = {
            "avg_msg_weekly": avg_msg_weekly,
            "avg_msg_monthly": avg_msg_monthly,
            "depth_label": depth_label,
            "depth_color": depth_color,
            "timeline": timeline_data,
            "total_messages": total_messages,
            "audio_count": audio_count,
            "audio_ratio": round(audio_ratio, 1)
        }
        cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Error compiling analytics for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
