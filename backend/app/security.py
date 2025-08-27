from __future__ import annotations

from cryptography.fernet import Fernet
from typing import Optional


def get_fernet(secret: str) -> Fernet:
    key = secret
    if len(secret) != 44:  # urlsafe_b64 key length for Fernet
        # Derive a Fernet key from arbitrary secret by padding/truncation
        import base64, hashlib
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(text: str, secret: str) -> str:
    f = get_fernet(secret)
    return f.encrypt(text.encode()).decode()


def decrypt(token: str, secret: str) -> str:
    f = get_fernet(secret)
    return f.decrypt(token.encode()).decode()

