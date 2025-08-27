"""Authentication API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ....config.logging import get_logger
from ....application.schemas.auth import LoginRequest, VerifyCodeRequest, LoginResponse, UserResponse
from ....application.schemas.common import SuccessResponse
from ....application.use_cases import AuthUseCases
from ....infrastructure.database.repositories import UserRepositoryImpl
from ....infrastructure.telegram.client import telegram_client_manager
from ....core.dependencies import get_db, verify_api_auth
from ....core.exceptions import AuthenticationError, TelegramError

logger = get_logger(__name__)
router = APIRouter()


def get_auth_use_cases(db: AsyncSession = Depends(get_db)) -> AuthUseCases:
    """Get auth use cases with dependencies."""
    user_repository = UserRepositoryImpl(db)
    return AuthUseCases(user_repository, telegram_client_manager)


@router.post("/send-code", response_model=SuccessResponse)
async def send_login_code(
    request: LoginRequest,
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Send login verification code to phone number."""
    try:
        result = await auth_use_cases.send_login_code(request.phone)
        logger.debug(f"Verification code sent to: {request.phone}")
        return SuccessResponse(
            message="Verification code sent successfully",
            data=result
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-code", response_model=LoginResponse)
async def verify_login_code(
    request: VerifyCodeRequest,
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Verify login code and create session."""
    try:
        result = await auth_use_cases.verify_login_code(
            phone=request.phone,
            code=request.code,
            phone_code_hash=request.phone_code_hash,
            password=request.password
        )
        return LoginResponse(
            session_encrypted=result["session_encrypted"],
            user_id=result["user_id"],
            username=result["username"]
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Get current user information."""
    try:
        user_info = await auth_use_cases.get_current_user()
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=user_info["id"],
            username=user_info["username"],
            created_at=user_info["created_at"],
            is_anonymous=user_info["is_anonymous"]
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/logout", response_model=SuccessResponse)
async def logout(
    auth_use_cases: AuthUseCases = Depends(get_auth_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Logout current user."""
    try:
        success = await auth_use_cases.logout()
        return SuccessResponse(
            message="Logged out successfully" if success else "Logout failed"
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
