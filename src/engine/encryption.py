"""Field-level encryption for sensitive clinical data using Fernet (AES-128-CBC).

Key is stored in the OS keyring under "Profile_Guru_Encryption" / "master_key".
If no key exists, one is generated on first use.
"""


from cryptography.fernet import Fernet, InvalidToken

from src.utils.logger import logger

_KEYRING_SERVICE = "Profile_Guru_Encryption"
_KEYRING_KEY = "master_key"


def _get_or_create_key() -> bytes | None:
    """Get the encryption key from the OS keyring, or generate and store one."""
    try:
        import keyring
        existing = keyring.get_password(_KEYRING_SERVICE, _KEYRING_KEY)
        if existing:
            return existing.encode("utf-8")
        # Generate and store a new key
        new_key = Fernet.generate_key()
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_KEY, new_key.decode("utf-8"))
        logger.info("Generated and stored new encryption master key in OS keyring")
        return new_key
    except Exception as e:
        logger.warning(f"Could not access OS keyring for encryption: {e}")
        return None


def _get_fernet() -> Fernet | None:
    key = _get_or_create_key()
    if key is None:
        return None
    try:
        return Fernet(key)
    except Exception as e:
        logger.error(f"Failed to create Fernet from key: {e}")
        return None


def encrypt(text: str) -> str | None:
    """Encrypt a string. Returns a base64-encoded ciphertext or None on failure."""
    if not text:
        return text
    f = _get_fernet()
    if f is None:
        return text  # fail open — encryption unavailable
    try:
        return f.encrypt(text.encode("utf-8")).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return text


def decrypt(ciphertext: str) -> str | None:
    """Decrypt a base64-encoded ciphertext. Returns plaintext or None on failure."""
    if not ciphertext:
        return ciphertext
    f = _get_fernet()
    if f is None:
        return ciphertext  # fail open
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        # Not encrypted or wrong key — return as-is
        return ciphertext
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return ciphertext


def is_encrypted(text: str) -> bool:
    """Check if a string looks like a Fernet-encrypted value (base64 with gAAAAA prefix)."""
    return text.startswith("gAAAAA") if text else False
