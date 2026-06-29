import os
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pathlib import Path
from src.utils.config import config
from src.utils.logger import logger
from src.api.api_dependencies import get_current_user
from src.utils.validation import validate_safe_param
from src.utils.redis_client import cache_get, cache_set
from src.services.contacts_service import build_contacts_list, parse_monthly_messages, get_contact_analytics

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])

@router.get("")
def get_contacts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by contact name"),
    sort: str = Query("last_date", description="Sort field"),
    current_user: dict = Depends(get_current_user),
):
    try:
        all_contacts = cache_get("contacts:list:all")
        if all_contacts is None:
            all_contacts = build_contacts_list()
            if all_contacts is None:
                all_contacts = []

        if search:
            search_lower = search.lower()
            all_contacts = [c for c in all_contacts if search_lower in c["name"].lower()]

        def sort_key(c):
            val = c.get(sort, c.get("last_date", ""))
            if val == "Never" or not val:
                return "0000-00-00"
            return val

        all_contacts.sort(key=sort_key, reverse=True)

        total = len(all_contacts)
        start = (page - 1) * limit
        end = start + limit
        page_contacts = all_contacts[start:end]
        pages = max(1, (total + limit - 1) // limit)

        return {
            "contacts": page_contacts,
            "total": total,
            "page": page,
            "pages": pages,
        }
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
def get_contact_messages(
    name: str,
    month: str,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=500, description="Messages per page"),
    current_user: dict = Depends(get_current_user),
):
    validate_safe_param(name, "contact")
    validate_safe_param(month, "month")
    file_path = Path(config.CHATS_DIR) / name / "Chats" / month
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Monthly log file not found")

    try:
        cache_key = f"messages:{name}:{month}"
        all_messages = cache_get(cache_key)

        if all_messages is None:
            all_messages = parse_monthly_messages(name, month)
            cache_set(cache_key, all_messages, ttl=120)

        total = len(all_messages)
        start = (page - 1) * limit
        end = start + limit
        page_messages = all_messages[start:end]
        pages = max(1, (total + limit - 1) // limit)

        return {
            "messages": page_messages,
            "total": total,
            "page": page,
            "pages": pages,
        }
    except Exception as e:
        logger.error(f"Error reading messages for {name} ({month}): {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{name}/analytics")
def get_contact_analytics_endpoint(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        cache_key = f"analytics:{name}"
        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        result = get_contact_analytics(name)
        cache_set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Error compiling analytics for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
