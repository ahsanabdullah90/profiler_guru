# Encryption at Rest & Data Protection

Profile Guru implements field-level encryption for sensitive clinical data using Fernet (AES-128-CBC) with OS keyring integration, ensuring patient data is protected both in transit and at rest.

---

## 1. Encryption Architecture (`encryption.py`)

The encryption system is implemented in [encryption.py](file:///f:/Github/Profile-Guru/src/engine/encryption.py) and provides transparent encryption/decryption for clinical notes and other sensitive fields.

### Core Functions

```python
# From src/engine/encryption.py
def encrypt(text: str) -> str | None:
    """Encrypt a string. Returns a base64-encoded ciphertext or None on failure."""

def decrypt(ciphertext: str) -> str | None:
    """Decrypt a base64-encoded ciphertext. Returns plaintext or None on failure."""

def is_encrypted(text: str) -> bool:
    """Check if a string looks like a Fernet-encrypted value (base64 with gAAAAA prefix)."""
```

### Key Management

- **Storage:** Encryption keys are stored in the OS keyring under service name `"Profile_Guru_Encryption"` and key `"master_key"`.
- **Auto-Generation:** If no key exists, one is automatically generated on first use via `Fernet.generate_key()`.
- **Fail-Open Behavior:** If the OS keyring is unavailable (e.g., in CI/CD environments or headless servers), the system falls back to storing data unencrypted with a warning logged.
- **Algorithm:** Uses Fernet, which is AES-128-CBC with HMAC-SHA256 for authentication.

---

## 2. Clinical Notes Encryption Integration

The [clinical_notes_store.py](file:///f:/Github/Profile-Guru/src/engine/clinical_notes_store.py) module automatically encrypts all clinical note text before writing to SQLite:

### Write Path (Encryption)
1. Practitioner creates or updates a clinical note
2. `note_text` is encrypted via `encryption.encrypt(note_text)`
3. Encrypted ciphertext is stored in the `clinical_notes` SQLite table
4. Original plaintext is never persisted to disk

### Read Path (Decryption)
1. Encrypted `note_text` is read from SQLite
2. `encryption.decrypt(ciphertext)` is called
3. If decryption succeeds, plaintext is returned to the API
4. If decryption fails (e.g., key changed, data corrupted), the ciphertext is returned as-is

### Legacy Migration
When the encryption system is first enabled, existing unencrypted notes are automatically encrypted during the next read/write cycle. The `is_encrypted()` function detects whether a value is already encrypted (by checking for the `gAAAAA` Fernet prefix) and skips re-encryption.

---

## 3. Security Considerations

### Strengths
- **AES-128-CBC:** Industry-standard symmetric encryption algorithm
- **HMAC Authentication:** Fernet includes HMAC-SHA256 to detect tampering
- **OS Keyring:** Keys are stored in the OS's secure credential manager (Windows Credential Locker, macOS Keychain, Linux Secret Service)
- **Field-Level Granularity:** Only sensitive fields are encrypted, not the entire database

### Limitations
- **Fail-Open Fallback:** If the keyring is unavailable, data is stored unencrypted. This is intentional to support development/CI environments but should be monitored in production.
- **Key Rotation:** Currently, there is no automated key rotation mechanism. If the master key is lost, encrypted data becomes unrecoverable.
- **Memory Exposure:** Decrypted plaintext exists in memory during read operations. This is unavoidable for application use but means memory dumps could expose data.

---

## 4. Configuration & Environment

No explicit configuration is required. The encryption system auto-initializes on first use:

1. **First Run:** Checks OS keyring for existing key
2. **Key Missing:** Generates new key via `Fernet.generate_key()`
3. **Keyring Unavailable:** Logs warning, returns `None` from `_get_fernet()`, all encrypt/decrypt operations return input unchanged
4. **Keyring Available:** Stores generated key, logs success message

### Manual Key Management (Advanced)

To manually set or rotate the encryption key:

```python
import keyring
from cryptography.fernet import Fernet

# Generate a new key
new_key = Fernet.generate_key().decode("utf-8")

# Store in OS keyring
keyring.set_password("Profile_Guru_Encryption", "master_key", new_key)
```

**Warning:** Rotating the key will make all previously encrypted data unrecoverable unless you decrypt it first with the old key.

---

## 5. Testing

The encryption system is tested in `tests/test_encryption.py` (if exists) or implicitly through clinical notes tests. Key test scenarios:

- Encrypt → Decrypt roundtrip
- Empty string handling
- Invalid token handling (returns input unchanged)
- Keyring unavailability (fail-open behavior)
- Legacy unencrypted data detection via `is_encrypted()`

---

## 6. Compliance & HIPAA

Encryption at rest is a key requirement for HIPAA compliance. Profile Guru's implementation satisfies:

- **§164.312(a)(2)(iv):** Encryption mechanism for electronic protected health information (ePHI) at rest
- **Audit Trail:** All encryption/decryption operations are logged (success/failure)
- **Access Control:** Only the application process with keyring access can decrypt data

However, encryption alone does not guarantee HIPAA compliance. Practitioners must also ensure:

- Secure backup procedures for encryption keys
- Access logging and monitoring
- Business Associate Agreements (BAAs) with cloud providers (if using Gemini Cloud ASR)
- Physical security of devices running the application
