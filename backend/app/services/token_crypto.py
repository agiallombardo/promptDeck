from __future__ import annotations

import base64
import hashlib

from app.config import Settings
from cryptography.fernet import Fernet


def _fernet(settings: Settings) -> Fernet:
    raw = settings.entra_token_encryption_key
    if raw:
        key = raw.encode()
    else:
        digest = hashlib.sha256(settings.jwt_secret_key.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_text(settings: Settings, plaintext: str) -> str:
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt_text(settings: Settings, ciphertext: str) -> str:
    return _fernet(settings).decrypt(ciphertext.encode()).decode()
