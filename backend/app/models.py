from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, ForeignKey, BigInteger, UniqueConstraint, Text, CheckConstraint, DateTime, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text('now()'))

    sessions: Mapped[list[TelegramSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    channels: Mapped[list[TelegramChannel]] = relationship(back_populates="user", cascade="all, delete-orphan")
    nodes: Mapped[list[Node]] = relationship(back_populates="user", cascade="all, delete-orphan")


class TelegramSession(Base):
    __tablename__ = "telegram_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    session_string_encrypted: Mapped[str] = mapped_column(String(8192))
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class TelegramChannel(Base):
    __tablename__ = "telegram_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    channel_id: Mapped[int] = mapped_column(BigInteger)  # e.g. -100xxxxxxxxxx
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # e.g. @channelname
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="channels")

    __table_args__ = (
        UniqueConstraint("user_id", "channel_id", name="uq_user_channel"),
    )


class Node(Base):
    """Unified table for both files and folders using adjacency list + materialized path"""
    __tablename__ = "nodes"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, server_default=text('gen_random_uuid()'))
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    parent_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("nodes.id", ondelete="RESTRICT"), nullable=True)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)  # 'folder' or 'file'
    path: Mapped[str] = mapped_column(Text)  # materialized path like 'root.folder1.subfolder2'
    depth: Mapped[Optional[int]] = mapped_column(Integer)  # computed from path
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

    user: Mapped[User] = relationship(back_populates="nodes")
    parent: Mapped[Optional[Node]] = relationship("Node", remote_side="Node.id", back_populates="children")
    children: Mapped[list[Node]] = relationship("Node", back_populates="parent")

    __table_args__ = (
        CheckConstraint("kind IN ('folder', 'file')", name="check_node_kind"),
    )

