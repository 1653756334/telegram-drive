"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from sqlalchemy import String, Integer, ForeignKey, BigInteger, UniqueConstraint, Text, CheckConstraint, DateTime, text, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...config.database import Base


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, Enum):
    """User status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class UserModel(Base):
    """User database model."""
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))

    # Authentication fields
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # User profile
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Role and status
    role: Mapped[UserRole] = mapped_column(String(20), default=UserRole.USER, server_default=text("'user'"))
    status: Mapped[UserStatus] = mapped_column(String(20), default=UserStatus.PENDING, server_default=text("'pending'"))

    # 移除 is_admin_password_set 字段，改为通过检查管理员用户是否存在且有密码来判断

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[list["TelegramSessionModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    channels: Mapped[list["TelegramChannelModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    nodes: Mapped[list["NodeModel"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def is_anonymous(self) -> bool:
        """Check if user is anonymous (no username set)."""
        return self.username is None

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == UserRole.ADMIN

    def is_active(self) -> bool:
        """Check if user is active."""
        return self.status == UserStatus.ACTIVE


class TelegramSessionModel(Base):
    """Telegram session database model."""
    __tablename__ = "telegram_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    # Telegram account info
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Session data
    session_string_encrypted: Mapped[str] = mapped_column(String(8192))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('false'))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[UserModel] = relationship(back_populates="sessions")


class TelegramChannelModel(Base):
    """Telegram channel database model."""
    __tablename__ = "telegram_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    channel_id: Mapped[int] = mapped_column(BigInteger)  # e.g. -100xxxxxxxxxx
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g. @channelname
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))

    # Relationships
    user: Mapped[UserModel] = relationship(back_populates="channels")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )


class NodeModel(Base):
    """Node database model for files and directories."""
    __tablename__ = "nodes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)  # 'folder' or 'file'
    path: Mapped[str] = mapped_column(Text)  # materialized path
    depth: Mapped[Optional[int]] = mapped_column(Integer)
    sort_key: Mapped[int] = mapped_column(Integer, server_default=text('0'))
    size_bytes: Mapped[int] = mapped_column(BigInteger, server_default=text('0'))
    
    # File-specific fields (null for folders)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    telegram_channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    telegram_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped[UserModel] = relationship(back_populates="nodes")
    parent: Mapped[Optional["NodeModel"]] = relationship("NodeModel", remote_side="NodeModel.id", back_populates="children")
    children: Mapped[list["NodeModel"]] = relationship("NodeModel", back_populates="parent")

    __table_args__ = (
        CheckConstraint("kind IN ('folder', 'file')", name="check_node_kind"),
    )
