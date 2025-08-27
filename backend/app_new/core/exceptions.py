"""Custom application exceptions."""

from typing import Any, Optional


class TelegramDriveException(Exception):
    """Base exception for Telegram Drive application."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AuthenticationError(TelegramDriveException):
    """Authentication related errors."""
    pass


class AuthorizationError(TelegramDriveException):
    """Authorization related errors."""
    pass


class NotFoundError(TelegramDriveException):
    """Resource not found errors."""
    pass


class ValidationError(TelegramDriveException):
    """Data validation errors."""
    pass


class TelegramError(TelegramDriveException):
    """Telegram API related errors."""
    pass


class StorageError(TelegramDriveException):
    """File storage related errors."""
    pass


class ConflictError(TelegramDriveException):
    """Resource conflict errors."""
    pass
