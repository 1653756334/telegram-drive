"""Admin API routes for user management."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....config.logging import get_logger
from ....application.schemas.auth import UserResponse
from ....application.schemas.common import SuccessResponse
from ....infrastructure.database.repositories import UserRepositoryImpl
from ....infrastructure.database.models import UserModel, UserStatus
from ....core.dependencies import get_db, get_current_admin_user
from ....core.exceptions import NotFoundError, ValidationError

logger = get_logger(__name__)
router = APIRouter()


class AdminUseCases:
    """Admin use cases for user management."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepositoryImpl(db)
    
    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[UserModel]:
        """Get all users with pagination."""
        from sqlalchemy import select
        from ....infrastructure.database.models import UserModel
        
        result = await self.db.execute(
            select(UserModel)
            .offset(skip)
            .limit(limit)
            .order_by(UserModel.created_at.desc())
        )
        return result.scalars().all()
    
    async def activate_user(self, user_id: UUID) -> UserModel:
        """Activate a user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if user.status == UserStatus.ACTIVE:
            raise ValidationError("User is already active")
        
        user.status = UserStatus.ACTIVE
        await self.user_repository.update(user)
        return user
    
    async def deactivate_user(self, user_id: UUID) -> UserModel:
        """Deactivate a user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if user.is_admin():
            raise ValidationError("Cannot deactivate admin user")
        
        if user.status == UserStatus.INACTIVE:
            raise ValidationError("User is already inactive")
        
        user.status = UserStatus.INACTIVE
        await self.user_repository.update(user)
        return user
    
    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        
        if user.is_admin():
            raise ValidationError("Cannot delete admin user")
        
        return await self.user_repository.delete(user_id)


def get_admin_use_cases(db: AsyncSession = Depends(get_db)) -> AdminUseCases:
    """Get admin use cases with dependencies."""
    return AdminUseCases(db)


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of users to return"),
    current_admin: UserModel = Depends(get_current_admin_user),
    admin_use_cases: AdminUseCases = Depends(get_admin_use_cases)
):
    """Get all users (admin only)."""
    try:
        users = await admin_use_cases.get_all_users(skip=skip, limit=limit)
        return [
            UserResponse(
                id=user.id,
                username=user.username or "",
                email=user.email,
                display_name=user.display_name,
                role=user.role,
                status=user.status,
                created_at=user.created_at.isoformat(),
                last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/users/{user_id}/activate", response_model=SuccessResponse)
async def activate_user(
    user_id: UUID,
    current_admin: UserModel = Depends(get_current_admin_user),
    admin_use_cases: AdminUseCases = Depends(get_admin_use_cases)
):
    """Activate a user (admin only)."""
    try:
        user = await admin_use_cases.activate_user(user_id)
        logger.info(f"User activated by admin {current_admin.username}: {user.username}")
        return SuccessResponse(
            message=f"User {user.username} activated successfully",
            data={"user_id": str(user.id), "status": user.status}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Activate user error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.post("/users/{user_id}/deactivate", response_model=SuccessResponse)
async def deactivate_user(
    user_id: UUID,
    current_admin: UserModel = Depends(get_current_admin_user),
    admin_use_cases: AdminUseCases = Depends(get_admin_use_cases)
):
    """Deactivate a user (admin only)."""
    try:
        user = await admin_use_cases.deactivate_user(user_id)
        logger.info(f"User deactivated by admin {current_admin.username}: {user.username}")
        return SuccessResponse(
            message=f"User {user.username} deactivated successfully",
            data={"user_id": str(user.id), "status": user.status}
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Deactivate user error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def delete_user(
    user_id: UUID,
    current_admin: UserModel = Depends(get_current_admin_user),
    admin_use_cases: AdminUseCases = Depends(get_admin_use_cases)
):
    """Delete a user (admin only)."""
    try:
        success = await admin_use_cases.delete_user(user_id)
        if success:
            logger.info(f"User deleted by admin {current_admin.username}: {user_id}")
            return SuccessResponse(
                message="User deleted successfully",
                data={"user_id": str(user_id)}
            )
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    current_admin: UserModel = Depends(get_current_admin_user),
    admin_use_cases: AdminUseCases = Depends(get_admin_use_cases)
):
    """Get user by ID (admin only)."""
    try:
        user = await admin_use_cases.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return UserResponse(
            id=user.id,
            username=user.username or "",
            email=user.email,
            display_name=user.display_name,
            role=user.role,
            status=user.status,
            created_at=user.created_at.isoformat(),
            last_login_at=user.last_login_at.isoformat() if user.last_login_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user by ID error: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
