"""Security utilities for encryption and authentication."""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from .exceptions import AuthenticationError
from ..config import get_settings


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


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Security manager for JWT and password operations."""

    def __init__(self):
        self.settings = get_settings()
        self.algorithm = self.settings.jwt_algorithm
        self.access_token_expire_minutes = self.settings.access_token_expire_minutes
        self.refresh_token_expire_days = 7
        # Use JWT secret key if available, otherwise fall back to session secret
        self.secret_key = self.settings.jwt_secret_key or self.settings.session_secret

    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("type") != token_type:
                return None

            # Check expiration
            exp = payload.get("exp")
            if exp is None:
                return None

            if datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
                return None

            return payload
        except JWTError:
            return None

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def create_token_pair(self, user_id: UUID, username: str, role: str) -> Dict[str, str]:
        """Create access and refresh token pair."""
        token_data = {
            "sub": str(user_id),
            "username": username,
            "role": role
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token({"sub": str(user_id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }


# Global security manager instance
security_manager = SecurityManager()


def get_password_hash(password: str) -> str:
    """Get password hash."""
    return security_manager.hash_password(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return security_manager.verify_password(plain_password, hashed_password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create access token."""
    return security_manager.create_access_token(data, expires_delta)


def verify_token(token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
    """Verify token."""
    return security_manager.verify_token(token, token_type)


# API token验证已移除，现在使用JWT认证
