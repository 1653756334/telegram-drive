"""FastAPI dependencies for core functionality."""

from typing import Optional

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..config.database import get_db_session
from .security import verify_api_token


async def get_db() -> AsyncSession:
    """Get database session dependency."""
    async for session in get_db_session():
        yield session


async def verify_api_auth(
    authorization: Optional[str] = Header(None),
    x_api_token: Optional[str] = Header(None)
) -> None:
    """Verify API authentication if required."""
    settings = get_settings()
    
    if not settings.api_token:
        return  # No authentication required
    
    # Try Authorization header first (Bearer token)
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]  # Remove "Bearer " prefix
    elif x_api_token:
        token = x_api_token
    
    if not verify_api_token(token, settings.api_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API token",
            headers={"WWW-Authenticate": "Bearer"}
        )
