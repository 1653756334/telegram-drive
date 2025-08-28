"""Authentication related schemas."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Legacy Telegram auth schemas (to be deprecated)
class TelegramLoginRequest(BaseModel):
    """Request to send login code."""
    phone: str = Field(..., description="Phone number in international format")


class TelegramVerifyCodeRequest(BaseModel):
    """Request to verify login code."""
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., description="Verification code")
    phone_code_hash: str = Field(..., description="Phone code hash from login request")
    password: Optional[str] = Field(None, description="2FA password if required")


# New JWT-based auth schemas
class LoginRequest(BaseModel):
    """User login request."""
    username: str = Field(..., description="Username or email")
    password: str = Field(..., description="Password")


class RegisterRequest(BaseModel):
    """User registration request."""
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    email: Optional[str] = Field(None, description="Email address")
    password: str = Field(..., min_length=6, description="Password")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")


class SetAdminPasswordRequest(BaseModel):
    """Set admin password request."""
    username: str = Field(..., description="Admin username for verification")
    password: str = Field(..., min_length=6, description="Admin password")


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=6, description="New password")


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    username: str = Field(..., description="Username or email")


class TokenRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


class UpdateProfileRequest(BaseModel):
    """Update user profile request."""
    email: Optional[str] = Field(None, description="Email address")
    display_name: Optional[str] = Field(None, max_length=100, description="Display name")


# Response schemas
class TokenResponse(BaseModel):
    """Token response."""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class LoginResponse(TokenResponse):
    """Login response with user info."""
    user_id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: str = Field(..., description="User role")
    display_name: Optional[str] = Field(None, description="Display name")


class UserResponse(BaseModel):
    """User information response."""
    id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    email: Optional[str] = Field(None, description="Email")
    display_name: Optional[str] = Field(None, description="Display name")
    role: str = Field(..., description="User role")
    status: str = Field(..., description="User status")
    created_at: str = Field(..., description="Creation timestamp")
    last_login_at: Optional[str] = Field(None, description="Last login timestamp")


class AdminStatusResponse(BaseModel):
    """Admin status response."""
    admin_exists: bool = Field(..., description="Whether admin user exists and has password")


# Legacy response schemas (to be deprecated)
class TelegramLoginResponse(BaseModel):
    """Telegram login response."""
    session_encrypted: str = Field(..., description="Encrypted session string")
    user_id: str = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")



