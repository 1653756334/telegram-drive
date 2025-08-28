"""User authentication use cases for JWT-based auth."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.auth import (
    LoginRequest, RegisterRequest, SetAdminPasswordRequest,
    ChangePasswordRequest, TokenRefreshRequest, UpdateProfileRequest
)
from ...core.security import security_manager, get_password_hash, verify_password
from ...core.exceptions import AuthenticationError, ValidationError, ConflictError
from ...infrastructure.database.repositories import UserRepositoryImpl
from ...infrastructure.database.models import UserRole, UserStatus
from ...config import get_settings
from ...config.logging import get_logger

logger = get_logger(__name__)


class UserAuthUseCases:
    """User authentication use cases."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repository = UserRepositoryImpl(db)
        self.settings = get_settings()
    
    async def login(self, request: LoginRequest) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        # Find user by username or email
        user = await self.user_repository.get_by_username_or_email(request.username)
        if not user:
            raise AuthenticationError("Invalid username or password")
        
        # Check password
        if not user.password_hash or not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid username or password")
        
        # Check if user is active
        if not user.is_active():
            if user.status == UserStatus.PENDING:
                raise AuthenticationError("Account is pending activation")
            else:
                raise AuthenticationError("Account is inactive")
        
        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.user_repository.update(user)
        
        # Create tokens
        tokens = security_manager.create_token_pair(
            user_id=user.id,
            username=user.username or "",
            role=user.role
        )
        
        logger.info(f"User login successful: {user.username}")
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": security_manager.access_token_expire_minutes * 60,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "display_name": user.display_name
        }
    
    async def register(self, request: RegisterRequest) -> Dict[str, Any]:
        """Register new user."""
        # Check if username already exists
        existing_user = await self.user_repository.get_by_username(request.username)
        if existing_user:
            raise ConflictError("Username already exists")
        
        # Check if email already exists (if provided)
        if request.email:
            existing_email = await self.user_repository.get_by_email(request.email)
            if existing_email:
                raise ConflictError("Email already exists")
        
        # Hash password
        password_hash = get_password_hash(request.password)
        
        # Create user
        user = await self.user_repository.create({
            "username": request.username,
            "email": request.email,
            "password_hash": password_hash,
            "display_name": request.display_name,
            "role": UserRole.USER,
            "status": UserStatus.PENDING  # Requires admin activation
        })
        
        logger.info(f"User registered: {user.username}")
        
        return {
            "user_id": user.id,
            "username": user.username,
            "status": user.status,
            "message": "Registration successful. Please wait for admin activation."
        }
    
    async def set_admin_password(self, request: SetAdminPasswordRequest) -> Dict[str, Any]:
        """Set admin password for first-time setup."""
        # 验证用户名是否匹配配置
        if request.username != self.settings.admin_username:
            raise ValidationError("Invalid admin username")

        # Check if admin user exists
        admin_user = await self.user_repository.get_by_username(self.settings.admin_username)

        if not admin_user:
            # Create admin user
            password_hash = get_password_hash(request.password)
            admin_user = await self.user_repository.create({
                "username": self.settings.admin_username,
                "password_hash": password_hash,
                "display_name": "Administrator",
                "role": UserRole.ADMIN,
                "status": UserStatus.ACTIVE
            })
            logger.info(f"Admin user created: {admin_user.username}")
        else:
            # Update existing admin user (only if no password is set)
            if admin_user.password_hash:
                raise ValidationError("Admin password is already set")

            admin_user.password_hash = get_password_hash(request.password)
            admin_user.status = UserStatus.ACTIVE
            await self.user_repository.update(admin_user)
            logger.info(f"Admin password set for: {admin_user.username}")

        return {
            "message": "Admin password set successfully",
            "admin_username": admin_user.username
        }
    
    async def refresh_token(self, request: TokenRefreshRequest) -> Dict[str, Any]:
        """Refresh access token using refresh token."""
        # Verify refresh token
        payload = security_manager.verify_token(request.refresh_token, "refresh")
        if not payload:
            raise AuthenticationError("Invalid refresh token")
        
        # Get user
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise AuthenticationError("Invalid refresh token")
        
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            raise AuthenticationError("Invalid refresh token")
        
        user = await self.user_repository.get_by_id(user_id)
        if not user or not user.is_active():
            raise AuthenticationError("User not found or inactive")
        
        # Create new tokens
        tokens = security_manager.create_token_pair(
            user_id=user.id,
            username=user.username or "",
            role=user.role
        )
        
        return {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
            "token_type": tokens["token_type"],
            "expires_in": security_manager.access_token_expire_minutes * 60
        }
    
    async def get_admin_status(self) -> Dict[str, Any]:
        """Get admin setup status."""
        admin_user = await self.user_repository.get_by_username(self.settings.admin_username)

        return {
            "admin_exists": bool(admin_user and admin_user.password_hash)
        }
    
    async def get_current_user_info(self, user_id: UUID) -> Dict[str, Any]:
        """Get current user information."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }

    async def update_profile(self, user_id: UUID, request: UpdateProfileRequest) -> Dict[str, Any]:
        """Update user profile."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")

        # Check if email already exists (if provided and different from current)
        if request.email and request.email != user.email:
            existing_email = await self.user_repository.get_by_email(request.email)
            if existing_email and existing_email.id != user.id:
                raise ConflictError("Email already exists")

        # Update fields
        if request.email is not None:
            user.email = request.email
        if request.display_name is not None:
            user.display_name = request.display_name

        await self.user_repository.update(user)

        logger.info(f"User profile updated: {user.username}")

        return {
            "message": "Profile updated successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "display_name": user.display_name,
                "role": user.role,
                "status": user.status
            }
        }
