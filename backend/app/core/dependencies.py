"""FastAPI dependencies for core functionality."""

from typing import Optional, AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..config.database import get_db_session
from ..config.logging import get_logger
from .security import verify_token
from ..infrastructure.database.repositories import UserRepositoryImpl
from ..infrastructure.database.models import UserModel, UserRole

logger = get_logger(__name__)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db_session():
        yield session


# JWT Bearer token security
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Verify JWT token
        payload = verify_token(credentials.credentials)
        if payload is None:
            raise credentials_exception

        # Get user ID from token
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise credentials_exception

        # Get user from database
        user_repo = UserRepositoryImpl(db)
        user_model = await user_repo.get_by_id(user_id)
        if user_model is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Convert to UserModel for compatibility
        # Note: We need to return UserModel, not User entity
        result = await db.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        # Check if user is active
        if not user.is_active():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_current_user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Get current active user."""
    return current_user


async def get_current_admin_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """Get current admin user."""
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


# API token验证已移除，现在使用JWT认证
