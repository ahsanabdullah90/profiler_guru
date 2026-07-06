"""Inspector data API — tags, notes, and star/archive flags per contact.

Backed by JSON storage in src.storage.inspector_store (see module docstring).
All routes require JWT authentication (existing middleware).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.api_dependencies import get_current_user
from src.engine.user_notes_embedder import user_notes_embedder
from src.storage.inspector_store import get_inspector_store
from src.utils.logger import logger
from src.utils.validation import validate_safe_param


router = APIRouter(prefix="/api/v1/inspector", tags=["Inspector"])


# ----------------------------- Schemas ----------------------------- #

class TagListResponse(BaseModel):
    contact: str
    tags: list[str]


class TagCreateRequest(BaseModel):
    tag: str = Field(..., min_length=1, max_length=64)


class NoteEntry(BaseModel):
    id: str
    note: str
    created_at: str
    updated_at: str


class NoteListResponse(BaseModel):
    contact: str
    notes: list[NoteEntry]


class NoteCreateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=10_000)


class NoteUpdateRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=10_000)


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
    validate_safe_param(contact_name, "contact")
    return TagListResponse(
        contact=contact_name,
        tags=get_inspector_store().get_tags(contact_name),
    )


@router.post("/{contact_name}/tags", response_model=TagListResponse, status_code=200)
def add_tag(
    contact_name: str,
    req: TagCreateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> TagListResponse:
    validate_safe_param(contact_name, "contact")
    try:
        tags = get_inspector_store().add_tag(contact_name, req.tag)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TagListResponse(contact=contact_name, tags=tags)


@router.delete("/{contact_name}/tags/{tag}", response_model=TagListResponse)
def remove_tag(
    contact_name: str,
    tag: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> TagListResponse:
    validate_safe_param(contact_name, "contact")
    validate_safe_param(tag, "tag")
    tags = get_inspector_store().remove_tag(contact_name, tag)
    return TagListResponse(contact=contact_name, tags=tags)


# ---------------------------- Helper ----------------------------- #

def _embed_note(contact_name: str, note: dict) -> None:
    """Embed a note into the user_notes ChromaDB collection."""
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
    validate_safe_param(contact_name, "contact")
    return NoteListResponse(
        contact=contact_name,
        notes=[NoteEntry(**n) for n in get_inspector_store().get_notes(contact_name)],
    )


@router.post("/{contact_name}/notes", response_model=NoteEntry, status_code=201)
def add_note(
    contact_name: str,
    req: NoteCreateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteEntry:
    validate_safe_param(contact_name, "contact")
    try:
        note = get_inspector_store().add_note(contact_name, req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _embed_note(contact_name, note)
    return NoteEntry(**note)


@router.put("/{contact_name}/notes/{note_id}", response_model=NoteEntry)
def update_note(
    contact_name: str,
    note_id: str,
    req: NoteUpdateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteEntry:
    validate_safe_param(contact_name, "contact")
    try:
        note = get_inspector_store().update_note(contact_name, note_id, req.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    _embed_note(contact_name, note)
    return NoteEntry(**note)


@router.delete("/{contact_name}/notes/{note_id}", response_model=NoteDeleteResponse)
def delete_note(
    contact_name: str,
    note_id: str,
    _user: dict[str, Any] = Depends(get_current_user),
) -> NoteDeleteResponse:
    validate_safe_param(contact_name, "contact")
    deleted = get_inspector_store().delete_note(contact_name, note_id)
    # Remove from RAG index
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
    validate_safe_param(contact_name, "contact")
    flags = get_inspector_store().get_flags(contact_name)
    return FlagsResponse(contact=contact_name, **flags)


@router.patch("/{contact_name}/flags", response_model=FlagsResponse)
def set_flags(
    contact_name: str,
    req: FlagsUpdateRequest,
    _user: dict[str, Any] = Depends(get_current_user),
) -> FlagsResponse:
    validate_safe_param(contact_name, "contact")
    flags = get_inspector_store().set_flags(
        contact_name,
        starred=req.starred,
        archived=req.archived,
    )
    return FlagsResponse(contact=contact_name, **flags)
