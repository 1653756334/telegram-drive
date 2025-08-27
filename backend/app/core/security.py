"""Security utilities for encryption and authentication."""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from .exceptions import AuthenticationError


def get_fernet(secret: str) -> Fernet:
    """Get Fernet cipher instance from secret."""
    key = secret
    if len(secret) != 44:  # urlsafe_b64 key length for Fernet
        # Derive a Fernet key from arbitrary secret by padding/truncation
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
    return Fernet(key)


def encrypt(text: str, secret: str) -> str:
    """Encrypt text using secret."""
    try:
        f = get_fernet(secret)
        return f.encrypt(text.encode()).decode()
    except Exception as e:
        raise AuthenticationError(f"Encryption failed: {e}")


def decrypt(token: str, secret: str) -> str:
    """Decrypt token using secret."""
    try:
        f = get_fernet(secret)
        return f.decrypt(token.encode()).decode()
    except Exception as e:
        raise AuthenticationError(f"Decryption failed: {e}")


def verify_api_token(provided_token: Optional[str], required_token: Optional[str]) -> bool:
    """Verify API token if required."""
    if not required_token:
        return True  # No token required
    
    if not provided_token:
        return False  # Token required but not provided
    
    return provided_token == required_token
