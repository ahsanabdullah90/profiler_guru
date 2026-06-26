import re
from fastapi import HTTPException

PARAM_REGEX = re.compile(r"^[a-zA-Z0-9_\-\. ]{1,100}$")

def validate_safe_param(value: str, param_name: str = "parameter") -> None:
    """Validates a path parameter against an alphanumeric, dash, dot, space regex to prevent path traversal."""
    if not value or not PARAM_REGEX.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid value for {param_name}. Must be 1-100 characters and contain only alphanumeric, underscores, dashes, dots, or spaces."
        )
