import os
import threading
from pathlib import Path
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Query
from src.api.api_dependencies import get_current_user
from src.services.contacts_service import (
    build_contacts_list,
    get_contact_analytics,
    parse_monthly_messages,
)
from src.utils.config import config
from src.utils.logger import logger
from src.utils.redis_client import cache_get, cache_set
from src.utils.task_tracker import task_tracker
from src.utils.validation import validate_safe_param
from src.engine.metrics_engine import MetricsEngine

IMPORT_LOCK = threading.Lock()

router = APIRouter(prefix="/api/v1/contacts", tags=["Contacts"])


class ImportRequest(BaseModel):
    path: str


@router.post("/import")
def submit_import(req: ImportRequest, current_user: dict = Depends(get_current_user)):
    """Submit a historical Instagram import task.
    Runs the import in a background thread; returns immediately.
    """
    if not IMPORT_LOCK.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="Import already running")

    # Pre-validate path before queuing
    import os
    if not req.path or not req.path.strip():
        IMPORT_LOCK.release()
        raise HTTPException(status_code=400, detail="Import path cannot be empty.")
    if not os.path.isdir(req.path.strip()):
        IMPORT_LOCK.release()
        raise HTTPException(status_code=400, detail=f"Path does not exist or is not a directory: {req.path}")

    task_id = "import_historical"

    def _run():
        try:
            from src.storage.storage_manager import StorageManager
            from src.engine.data_importer import InstagramDataImporter

            sm = StorageManager(config.CHATS_DIR)
            importer = InstagramDataImporter(sm)
            success = importer.import_from_json(req.path)
            if not success:
                task_tracker.fail_task(task_id, "Import returned False — see server logs")
        except Exception as e:
            logger.error(f"Import task failed: {e}")
            task_tracker.fail_task(task_id, str(e))
        finally:
            IMPORT_LOCK.release()

    task_tracker.register_task(task_id, "Historical Chat Import", task_type="import")
    threading.Thread(target=_run, daemon=True).start()
    return {"task_id": task_id, "status": "submitted"}


@router.get("")
def get_contacts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    search: str | None = Query(None, description="Search by contact name"),
    sort: str = Query("last_date", description="Sort field"),
    platform: str | None = Query(None, description="Filter by platform: 'instagram' or 'whatsapp'"),
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
            all_contacts = [
                c for c in all_contacts
                if search_lower in c["name"].lower()
                or (c.get("display_name") and search_lower in c["display_name"].lower())
                or (c.get("instagram_handle") and search_lower in c["instagram_handle"].lower())
            ]

        if platform:
            platform_lower = platform.lower()
            all_contacts = [
                c for c in all_contacts
                if platform_lower in c.get("platforms", [])
            ]

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


# -------- Client Profile Endpoints --------

class ProfileUpdate(BaseModel):
    display_name: str | None = None
    email: str | None = None
    mobile: str | None = None
    whatsapp: str | None = None
    instagram_handle: str | None = None


@router.get("/{name}/profile")
def get_client_profile(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        me = MetricsEngine()
        profile = me.get_client_profile(name)
        if profile is None:
            return {}
        # Convert photo_path to URL
        if profile.get("photo_path"):
            filename = os.path.basename(profile["photo_path"])
            profile["photo_url"] = f"/static/photos/{filename}"
        else:
            profile["photo_url"] = None
        del profile["photo_path"]
        return profile
    except Exception as e:
        logger.error(f"Error getting profile for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{name}/profile")
def update_client_profile(name: str, body: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        me = MetricsEngine()
        me.upsert_client_profile(
            chat_name=name,
            display_name=body.display_name,
            email=body.email,
            mobile=body.mobile,
            whatsapp=body.whatsapp,
            instagram_handle=body.instagram_handle,
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error updating profile for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi import UploadFile as FastAPIUploadFile, File


@router.post("/{name}/photo")
async def upload_client_photo(name: str, file: FastAPIUploadFile = File(...), current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_TYPES)}")

    if file.size is not None and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")

    import hashlib
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    safe_filename = hashlib.sha256(name.encode()).hexdigest()[:16] + ext
    photo_dir = Path(config.DATA_DIR) / "profile_photos"
    os.makedirs(photo_dir, exist_ok=True)
    dest = photo_dir / safe_filename

    try:
        content = await file.read()
        with open(dest, "wb") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save photo for {name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save photo")

    me = MetricsEngine()
    me.update_client_profile_photo(name, str(dest))
    return {"photo_url": f"/static/photos/{safe_filename}"}


@router.delete("/{name}/photo")
def delete_client_photo(name: str, current_user: dict = Depends(get_current_user)):
    validate_safe_param(name, "contact")
    try:
        me = MetricsEngine()
        profile = me.get_client_profile(name)
        if profile and profile.get("photo_path"):
            photo_path = Path(profile["photo_path"])
            if photo_path.exists():
                photo_path.unlink()
        me.delete_client_profile_photo(name)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error deleting photo for {name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -------- Contact Merge Endpoints --------


class MergeRequest(BaseModel):
    primary_chat_name: str
    secondary_chat_name: str


@router.post("/merge")
def merge_contacts_endpoint(req: MergeRequest, current_user: dict = Depends(get_current_user)):
    """Merge all data from secondary contact into primary, then delete secondary."""
    validate_safe_param(req.primary_chat_name, "contact")
    validate_safe_param(req.secondary_chat_name, "contact")
    if req.primary_chat_name == req.secondary_chat_name:
        raise HTTPException(status_code=400, detail="Cannot merge a contact with itself")
    try:
        from src.services.contact_merge import merge_contacts
        result = merge_contacts(req.primary_chat_name, req.secondary_chat_name)
        return result
    except Exception as e:
        logger.error(f"Merge error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# -------- Pending Merge Suggestions --------


@router.get("/pending-merges")
def get_pending_merges(current_user: dict = Depends(get_current_user)):
    """Return all pending merge suggestions."""
    try:
        metrics = MetricsEngine()
        return {"pending_merges": metrics.get_pending_merges()}
    except Exception as e:
        logger.error(f"Error fetching pending merges: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


class PendingMergeAction(BaseModel):
    suggestion_id: int


@router.post("/pending-merges/dismiss")
def dismiss_pending_merge(req: PendingMergeAction, current_user: dict = Depends(get_current_user)):
    """Dismiss a merge suggestion."""
    try:
        metrics = MetricsEngine()
        metrics.dismiss_pending_merge(req.suggestion_id)
        return {"status": "dismissed"}
    except Exception as e:
        logger.error(f"Error dismissing merge suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pending-merges/confirm")
def confirm_pending_merge(req: PendingMergeAction, current_user: dict = Depends(get_current_user)):
    """Confirm a merge suggestion and execute the merge."""
    try:
        metrics = MetricsEngine()
        suggestions = metrics.get_pending_merges()
        target = None
        for s in suggestions:
            if s["suggestion_id"] == req.suggestion_id:
                target = s
                break
        if not target:
            raise HTTPException(status_code=404, detail="Merge suggestion not found")

        from src.services.contact_merge import merge_contacts
        result = merge_contacts(target["existing_chat_name"], target["new_chat_name"])
        return {"status": "merged", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming merge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
