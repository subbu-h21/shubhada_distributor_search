"""Encryption helpers for storing distributor credentials at rest."""
import os
from cryptography.fernet import Fernet, InvalidToken

_KEY = os.environ.get("ENCRYPTION_KEY")
if not _KEY:
    raise RuntimeError("ENCRYPTION_KEY missing in backend/.env")

_fernet = Fernet(_KEY.encode() if isinstance(_KEY, str) else _KEY)


def encrypt_secret(plain: str) -> str:
    if plain is None:
        return None
    return _fernet.encrypt(plain.encode()).decode()


def decrypt_secret(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet.decrypt(token.encode()).decode()
    except InvalidToken:
        raise ValueError("Failed to decrypt secret (invalid token or key)")
