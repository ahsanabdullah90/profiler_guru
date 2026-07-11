"""Inspector data API — tags, notes, and star/archive flags per contact.

Notes are backed by SQLite (clinical_notes_store). Tags and flags remain in
JSON (inspector_store) since they are not clinical data.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from src.api.api_dependencies import get_current_user, resolve_contact
from src.engine.clinical_notes_store import ClinicalNotesStore
from src.engine.user_notes_embedder import user_notes_embedder
from src.storage.inspector_store import get_inspector_store
from src.utils.logger import logger
from src.utils.validation import validate_safe_param

router = APIRouter(prefix="/api/v1/inspector", tags=["Inspector"])
_notes_db = ClinicalNotesStore()

NOTE_TYPES = frozenset(["free", "soap", "dap", "progress"])


# ----------------------------- Schemas ----------------------------- #

class TagListResponse(BaseModel):
    contact: str
    tags: list[str]


class TagCreateRequest(BaseModel):
    tag: str = Field(..., min_length=1, max_length=64)


class NoteEntry(BaseModel):
    id: str
    note: str
    session_date: str | None = None
    note_type: str = "free"
    consent_version: str | None = None
    created_at: str
    updated_at: str
    revised_from: str | None = None


class NoteListResponse(BaseModel):
    contact: str
    notes: list[NoteEntry]


class NoteCreateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=10_000)
    session_date: str | None = None
    note_type: str = "free"
    consent_version: str | None = None

    @field_validator("note_type")
    @classmethod
    def validate_note_type(cls, v: str) -> str:
        if v not in NOTE_TYPES:
            raise ValueError(f"note_type must be one of: {', '.join(sorted(NOTE_TYPES))}")
        return v

    @field_validator("session_date")
    @classmethod
    def validate_session_date(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError("session_date must be YYYY-MM-DD format")
        return v


class NoteUpdateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=10_000)
    session_date: str | None = None
    note_type: str | None = None

    @field_validator("note_type")
    @classmethod
    def validate_note_type(cls, v: str | None) -> str | None:
        if v is not None and v not in NOTE_TYPES:
            raise ValueError(f"note_type must be one of: {', '.join(sorted(NOTE_TYPES))}")
        return v

    @field_validator("session_date")
    @classmethod
    def validate_session_date(cls, v: str | None) -> str | None:
        if v is not None:
            import re
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                raise ValueError("session_date must be YYYY-MM-DD format")
        return v


class NoteDeleteResponse(BaseModel):
    deleted: bool
    note_id: str


class FlagsResponse(BaseModel):
    contact: str
    starred: bool
    archived: bool


class FlagsUpdateRequest(BaseModel):
    starred: bool | None = None
    archived: bool | None = None


# ------------------------------ Tags ------------------------------ #

@router.get("/{contact_name}/tags", response_model=TagListResponse)
def get_tags(
    contact_name: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> TagListResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    return TagListResponse(
        contact=resolved,
        tags=get_inspector_store().get_tags(resolved),
    )


@router.post("/{contact_name}/tags", response_model=TagListResponse, status_code=200)
def add_tag(
    contact_name: str,
    req: TagCreateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> TagListResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    try:
        tags = get_inspector_store().add_tag(resolved, req.tag)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TagListResponse(contact=resolved, tags=tags)


@router.delete("/{contact_name}/tags/{tag}", response_model=TagListResponse)
def remove_tag(
    contact_name: str,
    tag: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> TagListResponse:
    validate_safe_param(tag, "tag")
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    tags = get_inspector_store().remove_tag(resolved, tag)
    return TagListResponse(contact=resolved, tags=tags)


# ---------------------------- Helper ----------------------------- #

def _embed_note(contact_name: str, note: dict) -> None:
    """Embed a clinical note into the user_notes ChromaDB collection."""
    try:
        title = note.get("note", "")[:80]
        content = note.get("note", "")
        user_notes_embedder.embed_note(
            contact_name=contact_name,
            note_id=note["id"],
            title=title,
            content=content,
            created_at=note["created_at"],
            updated_at=note["updated_at"],
        )
    except Exception as e:
        logger.warning(f"Failed to embed note {note.get('id')}: {e}")


# ----------------------------- Notes ----------------------------- #

@router.get("/{contact_name}/notes", response_model=NoteListResponse)
def get_notes(
    contact_name: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteListResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    notes = _notes_db.get_notes(resolved)
    return NoteListResponse(
        contact=resolved,
        notes=[NoteEntry(**n) for n in notes],
    )


@router.post("/{contact_name}/notes", response_model=NoteEntry, status_code=201)
def add_note(
    contact_name: str,
    req: NoteCreateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteEntry:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    try:
        note = _notes_db.add_note(
            contact_name=resolved,
            note_text=req.note,
            session_date=req.session_date,
            note_type=req.note_type,
            consent_version=req.consent_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _embed_note(resolved, note)
    return NoteEntry(**note)


@router.put("/{contact_name}/notes/{note_id}", response_model=NoteEntry)
def update_note(
    contact_name: str,
    note_id: str,
    req: NoteUpdateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteEntry:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    try:
        note = _notes_db.update_note(
            contact_name=resolved,
            note_id=note_id,
            note_text=req.note,
            session_date=req.session_date,
            note_type=req.note_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _embed_note(resolved, note)
    return NoteEntry(**note)


@router.delete("/{contact_name}/notes/{note_id}", response_model=NoteDeleteResponse)
def delete_note(
    contact_name: str,
    note_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteDeleteResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    deleted = _notes_db.delete_note(resolved, note_id)
    if deleted:
        try:
            user_notes_embedder.delete_note(note_id)
        except Exception as e:
            logger.warning(f"Failed to delete note vectors for {note_id}: {e}")
    return NoteDeleteResponse(deleted=deleted, note_id=note_id)


# ----------------------------- Flags ----------------------------- #

@router.get("/{contact_name}/flags", response_model=FlagsResponse)
def get_flags(
    contact_name: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> FlagsResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    flags = get_inspector_store().get_flags(resolved)
    return FlagsResponse(contact=resolved, **flags)


@router.patch("/{contact_name}/flags", response_model=FlagsResponse)
def set_flags(
    contact_name: str,
    req: FlagsUpdateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> FlagsResponse:
    _, cname = resolve_contact(contact_name)
    resolved = cname or contact_name
    validate_safe_param(resolved, "contact")
    flags = get_inspector_store().set_flags(
        resolved,
        starred=req.starred,
        archived=req.archived,
    )
    return FlagsResponse(contact=resolved, **flags)
