import re
import uuid as _uuid

CONTACT_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\. ]{1,100}$")
UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def sanitize_contact_name(name: str) -> str:
    sanitized = "".join(
        c if c.isalnum() or c in "_-. " else "_"
        for c in name
    ).strip(". ")
    if not sanitized:
        return "unknown"
    return sanitized[:100]


def is_valid_contact_name(name: str) -> bool:
    return bool(name and CONTACT_NAME_REGEX.match(name))


def is_valid_uuid(value: str) -> bool:
    return bool(value and UUID_REGEX.match(value))


def generate_client_id() -> str:
    return str(_uuid.uuid4())
