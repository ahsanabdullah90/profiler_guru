import re
import uuid as _uuid

# Matches any Unicode word character (letters, digits, _ from any script),
# plus hyphen, dot, and space. Re.UNICODE is the default in Python 3 but
# stated explicitly for clarity.
#
# Previously this was ASCII-only [a-zA-Z0-9_\-\. ] which caused a false-positive
# 'needs_migration' flag on contacts whose Instagram display names contain
# Arabic, Urdu, or accented characters — all of which pass sanitize_contact_name()
# (which uses Python's Unicode-aware str.isalnum()) but fail an ASCII regex.
CONTACT_NAME_REGEX = re.compile(r"^[\w\-\. ]{1,100}$", re.UNICODE)
UUID_REGEX = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def sanitize_contact_name(name: str) -> str:
    """Replace any character that is not a Unicode word char, hyphen, dot, or space with '_'.
    Strips leading/trailing dots and spaces. Returns 'unknown' for empty results.
    """
    sanitized = "".join(
        c if c.isalnum() or c in "_-. " else "_"
        for c in name
    ).strip(". ")
    if not sanitized:
        return "unknown"
    return sanitized[:100]


def is_valid_contact_name(name: str) -> bool:
    """Return True if *name* is a non-empty string that matches CONTACT_NAME_REGEX.

    Accepts any Unicode letter/digit (Arabic, Urdu, accented chars, etc.) plus
    underscore, hyphen, dot, and space — consistent with sanitize_contact_name().
    """
    return bool(name and CONTACT_NAME_REGEX.match(name))



def is_valid_uuid(value: str) -> bool:
    return bool(value and UUID_REGEX.match(value))


def generate_client_id() -> str:
    return str(_uuid.uuid4())
