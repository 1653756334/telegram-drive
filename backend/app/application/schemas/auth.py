"""Authentication related schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request to send login code."""
    phone: str = Field(..., description="Phone number in international format")


class VerifyCodeRequest(BaseModel):
    """Request to verify login code."""
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., description="Verification code")
    phone_code_hash: str = Field(..., description="Phone code hash from login request")
    password: Optional[str] = Field(None, description="2FA password if required")


class LoginResponse(BaseModel):
    """Login response."""
    session_encrypted: str = Field(..., description="Encrypted session string")
    user_id: str = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")


class UserResponse(BaseModel):
    """User information response."""
    id: str = Field(..., description="User ID")
    username: Optional[str] = Field(None, description="Username")
    created_at: str = Field(..., description="Creation timestamp")
    is_anonymous: bool = Field(..., description="Whether user is anonymous")
