"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....config.logging import get_logger
from ....application.schemas.auth import (
    LoginRequest, RegisterRequest, SetAdminPasswordRequest, TokenRefreshRequest,
    UpdateProfileRequest, LoginResponse, TokenResponse, UserResponse, AdminStatusResponse
)
from ....application.schemas.common import SuccessResponse
from ....application.use_cases.user_auth_use_cases import UserAuthUseCases
from ....infrastructure.database.repositories import UserRepositoryImpl
from ....infrastructure.database.models import UserModel
from ....core.dependencies import get_db, get_current_user, get_current_admin_user
from ....core.exceptions import AuthenticationError, ValidationError, ConflictError

logger = get_logger(__name__)
router = APIRouter()


# Removed deprecated AuthUseCases dependency


def get_user_auth_use_cases(db: AsyncSession = Depends(get_db)) -> UserAuthUseCases:
    """Get user auth use cases with dependencies."""
    return UserAuthUseCases(db)


# New JWT-based authentication endpoints
@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """User login with username/password."""
    try:
        result = await user_auth_use_cases.login(request)
        return LoginResponse(**result)
    except AuthenticationError as e:
        logger.debug(f"Login failed: {e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/register", response_model=SuccessResponse)
async def register(
    request: RegisterRequest,
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """User registration."""
    try:
        result = await user_auth_use_cases.register(request)
        return SuccessResponse(message=result["message"], data=result)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/admin/setup", response_model=SuccessResponse)
async def setup_admin(
    request: SetAdminPasswordRequest,
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """Set admin password for first-time setup."""
    try:
        result = await user_auth_use_cases.set_admin_password(request)
        return SuccessResponse(message=result["message"], data=result)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Admin setup error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/admin/status", response_model=AdminStatusResponse)
async def get_admin_status(
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """Get admin setup status."""
    try:
        result = await user_auth_use_cases.get_admin_status()
        return AdminStatusResponse(**result)
    except Exception as e:
        logger.error(f"Admin status error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """Refresh access token."""
    try:
        result = await user_auth_use_cases.refresh_token(request)
        return TokenResponse(**result)
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username or "",
        email=current_user.email,
        display_name=current_user.display_name,
        role=current_user.role,
        status=current_user.status,
        created_at=current_user.created_at.isoformat(),
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None
    )


@router.put("/me", response_model=SuccessResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: UserModel = Depends(get_current_user),
    user_auth_use_cases: UserAuthUseCases = Depends(get_user_auth_use_cases)
):
    """Update current user profile."""
    try:
        result = await user_auth_use_cases.update_profile(current_user.id, request)
        return SuccessResponse(message=result["message"], data=result.get("user"), success=True)
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Update profile error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    current_user: UserModel = Depends(get_current_user)
):
    """Logout current user."""
    # For JWT-based auth, logout is handled client-side by removing the token
    # Server-side logout would require token blacklisting which is not implemented
    return SuccessResponse(
        success=True,
        message="Logged out successfully",
        data=None
    )
