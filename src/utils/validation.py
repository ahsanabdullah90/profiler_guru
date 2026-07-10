from src.utils.sanitize import is_valid_contact_name, is_valid_uuid
from fastapi import HTTPException


def validate_safe_param(value: str, param_name: str = "parameter") -> None:
    """Validates a path parameter against the shared contact name regex or UUID."""
    if not value:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {param_name}. Must be a valid contact name or UUID."
        )
    if is_valid_uuid(value):
        return
    if not is_valid_contact_name(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {param_name}. Must be 1-100 characters and contain only alphanumeric, underscores, dashes, dots, or spaces."
        )
