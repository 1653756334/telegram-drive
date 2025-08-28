"""Telegram account management API routes."""

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from ....config.logging import get_logger
from ....application.schemas.auth import TelegramLoginRequest, TelegramVerifyCodeRequest
from ....application.schemas.common import SuccessResponse
from ....infrastructure.database.repositories import UserRepositoryImpl
from ....infrastructure.database.models import UserModel, TelegramSessionModel
from ....core.dependencies import get_db, get_current_user
from ....core.exceptions import NotFoundError, ValidationError, ConflictError, AuthenticationError, TelegramError
from ....application.use_cases.telegram_use_cases import TelegramUseCases
from ....core.security import encrypt, decrypt
from ....config import get_settings

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()

# Response schemas
class TelegramAccountResponse(BaseModel):
    """Telegram账户响应."""
    id: str = Field(..., description="账户ID")
    phone: str = Field(..., description="手机号")
    username: Optional[str] = Field(None, description="用户名")
    display_name: Optional[str] = Field(None, description="显示名称")
    is_active: bool = Field(..., description="是否为活跃账户")
    created_at: str = Field(..., description="创建时间")

class TelegramAccountsResponse(BaseModel):
    """Telegram账户列表响应."""
    accounts: List[TelegramAccountResponse] = Field(..., description="账户列表")
    active_account: Optional[TelegramAccountResponse] = Field(None, description="当前活跃账户")


# Dependencies
async def get_telegram_use_cases(db: AsyncSession = Depends(get_db)) -> TelegramUseCases:
    """Get Telegram use cases dependency."""
    from ....infrastructure.database.repositories import UserRepositoryImpl
    from ....infrastructure.telegram import TelegramClientManager

    user_repository = UserRepositoryImpl(db)
    telegram_manager = TelegramClientManager()
    return TelegramUseCases(user_repository, telegram_manager)


@router.get("/accounts", response_model=TelegramAccountsResponse)
async def get_telegram_accounts(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取用户的所有Telegram账户."""
    try:
        from sqlalchemy import select

        # 获取用户的所有Telegram会话
        result = await db.execute(
            select(TelegramSessionModel).where(TelegramSessionModel.user_id == current_user.id)
        )
        sessions = result.scalars().all()

        accounts = []
        active_account = None

        for session in sessions:
            account = TelegramAccountResponse(
                id=str(session.id),
                phone=session.phone,
                username=session.username,
                display_name=session.display_name,
                is_active=session.is_active,
                created_at=session.created_at.isoformat()
            )
            accounts.append(account)

            if session.is_active:
                active_account = account

        return TelegramAccountsResponse(
            accounts=accounts,
            active_account=active_account
        )
    except Exception as e:
        logger.error(f"Get telegram accounts error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/active-account", response_model=TelegramAccountResponse)
async def get_active_telegram_account(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取当前活跃的Telegram账户."""
    try:
        from sqlalchemy import select

        result = await db.execute(
            select(TelegramSessionModel).where(
                TelegramSessionModel.user_id == current_user.id,
                TelegramSessionModel.is_active == True
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active account found")

        return TelegramAccountResponse(
            id=str(session.id),
            phone=session.phone,
            username=session.username,
            display_name=session.display_name,
            is_active=True,
            created_at=session.created_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get active telegram account error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/accounts/{account_id}/activate", response_model=SuccessResponse)
async def activate_telegram_account(
    account_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """设置指定的Telegram账户为活跃账户."""
    try:
        from sqlalchemy import select, update

        # 检查账户是否存在且属于当前用户
        result = await db.execute(
            select(TelegramSessionModel).where(
                TelegramSessionModel.id == int(account_id),
                TelegramSessionModel.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        # 先将所有账户设为非活跃
        await db.execute(
            update(TelegramSessionModel)
            .where(TelegramSessionModel.user_id == current_user.id)
            .values(is_active=False)
        )

        # 设置指定账户为活跃
        await db.execute(
            update(TelegramSessionModel)
            .where(TelegramSessionModel.id == int(account_id))
            .values(is_active=True)
        )

        await db.commit()

        logger.info(f"User {current_user.username} activated Telegram account: {session.phone}")

        return SuccessResponse(
            success=True,
            message="Account activated successfully",
            data={"account_id": account_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Activate telegram account error: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/accounts/{account_id}", response_model=SuccessResponse)
async def delete_telegram_account(
    account_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除指定的Telegram账户."""
    try:
        from sqlalchemy import select, delete

        # 检查账户是否存在且属于当前用户
        result = await db.execute(
            select(TelegramSessionModel).where(
                TelegramSessionModel.id == int(account_id),
                TelegramSessionModel.user_id == current_user.id
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

        # 删除账户
        await db.execute(
            delete(TelegramSessionModel).where(TelegramSessionModel.id == int(account_id))
        )

        await db.commit()

        logger.info(f"User {current_user.username} deleted Telegram account: {session.phone}")

        return SuccessResponse(
            success=True,
            message="Account deleted successfully",
            data={"account_id": account_id}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete telegram account error: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/send-code", response_model=SuccessResponse)
async def send_telegram_login_code(
    request: TelegramLoginRequest,
    current_user: UserModel = Depends(get_current_user),
    telegram_use_cases: TelegramUseCases = Depends(get_telegram_use_cases)
):
    """发送Telegram登录验证码."""
    try:
        result = await telegram_use_cases.send_login_code(request.phone)
        logger.info(f"User {current_user.username} requested login code for: {request.phone}")

        return SuccessResponse(
            success=True,
            message="Verification code sent successfully",
            data=result
        )
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Send telegram login code error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to send verification code")


@router.post("/verify-code", response_model=SuccessResponse)
async def verify_telegram_login_code(
    request: TelegramVerifyCodeRequest,
    current_user: UserModel = Depends(get_current_user),
    telegram_use_cases: TelegramUseCases = Depends(get_telegram_use_cases),
    db: AsyncSession = Depends(get_db)
):
    """验证Telegram登录码并添加账户."""
    try:
        # 验证登录码并获取会话信息
        result = await telegram_use_cases.verify_login_code(
            phone=request.phone,
            code=request.code,
            phone_code_hash=request.phone_code_hash,
            password=request.password
        )

        # 检查是否已存在相同手机号的账户
        from sqlalchemy import select
        existing_result = await db.execute(
            select(TelegramSessionModel).where(
                TelegramSessionModel.user_id == current_user.id,
                TelegramSessionModel.phone == request.phone
            )
        )
        existing_session = existing_result.scalar_one_or_none()

        if existing_session:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists")

        # 创建新的Telegram会话记录
        new_session = TelegramSessionModel(
            user_id=current_user.id,
            phone=request.phone,
            telegram_user_id=result.get("telegram_user_id"),
            username=result.get("username"),
            display_name=result.get("display_name"),
            session_string_encrypted=result["session_encrypted"],
            is_active=False  # 新添加的账户默认不激活
        )

        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)

        logger.info(f"User {current_user.username} added Telegram account: {request.phone}")

        return SuccessResponse(
            success=True,
            message="Account added successfully",
            data={
                "account_id": str(new_session.id),
                "phone": request.phone,
                "username": result.get("username")
            }
        )
    except HTTPException:
        raise
    except AuthenticationError as e:
        # Telegram验证码错误应该是400而不是401
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Verify telegram login code error: {e}")
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to verify code")
