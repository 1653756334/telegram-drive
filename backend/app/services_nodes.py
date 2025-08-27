from __future__ import annotations

from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from pyrogram.client import Client
from pyrogram.types import ChatPrivileges
from pyrogram.errors import UserRestricted

from .models import User, TelegramSession, TelegramChannel, Node
from .config import get_settings
from .security import decrypt
from .telegram import telegram_manager


async def get_single_user(db: AsyncSession) -> User | None:
    res = await db.execute(select(User).limit(1))
    return res.scalar_one_or_none()


async def get_or_create_single_user(db: AsyncSession) -> User:
    """
    Get or create a single user for this system.
    In single-user mode, we create one user to own all data.
    This user will be updated with real info when they log in.
    """
    u = await get_single_user(db)
    if u:
        return u

    # Create a default user for single-user mode
    # This will be updated when the user actually logs in
    u = User(username="default_user")
    db.add(u)
    await db.flush()
    return u


async def update_user_info(db: AsyncSession, user_id: UUID, username: str | None) -> User | None:
    """Update user information after login"""
    res = await db.execute(select(User).where(User.id == user_id).limit(1))
    user = res.scalar_one_or_none()
    if user:
        user.username = username
        await db.commit()
        await db.refresh(user)
    return user


async def get_latest_session(db: AsyncSession) -> str | None:
    res = await db.execute(select(TelegramSession).order_by(TelegramSession.id.desc()).limit(1))
    row = res.scalar_one_or_none()
    if not row:
        return None
    settings = get_settings()
    return decrypt(row.session_string_encrypted, settings.session_secret)


async def get_storage_channel_id(db: AsyncSession) -> int | None:
    res = await db.execute(select(TelegramChannel).order_by(TelegramChannel.id.desc()).limit(1))
    row = res.scalar_one_or_none()
    return row.channel_id if row else None


async def get_storage_channel_info(db: AsyncSession) -> tuple[int, str | None] | None:
    """Get storage channel ID and username (if available)"""
    res = await db.execute(select(TelegramChannel).order_by(TelegramChannel.id.desc()).limit(1))
    row = res.scalar_one_or_none()
    if row:
        return (row.channel_id, row.username)
    return None


def _normalize_path(path: str) -> str:
    """Normalize directory path"""
    p = (path or "/").strip()
    if not p.startswith("/"):
        p = "/" + p
    # remove trailing slash except root
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


async def ensure_directory(db: AsyncSession, user_id: UUID, path: str) -> UUID | None:
    """Ensure directory tree exists for a logical path like '/a/b'. Return leaf directory id or None for root."""
    path = _normalize_path(path)
    if path == "/":
        return None

    # Check if directory already exists
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.kind == "folder",
            Node.path == path,
            Node.deleted_at.is_(None)
        ).limit(1)
    )
    existing = res.scalar_one_or_none()
    if existing:
        return existing.id

    # Create directory tree
    parts = [p for p in path.split("/") if p]
    current_path = ""
    parent_id = None

    for i, part in enumerate(parts):
        current_path = "/" + "/".join(parts[:i+1])

        # Check if this level exists
        res = await db.execute(
            select(Node).where(
                Node.user_id == user_id,
                Node.kind == "folder",
                Node.path == current_path,
                Node.deleted_at.is_(None)
            ).limit(1)
        )
        node = res.scalar_one_or_none()

        if not node:
            # Create this directory level
            node = Node(
                user_id=user_id,
                parent_id=parent_id,
                name=part,
                kind="folder",
                path=current_path,
                depth=i + 1
            )
            db.add(node)
            await db.flush()

        parent_id = node.id

    return parent_id


async def save_file_record(
    db: AsyncSession,
    *,
    user_id: UUID,
    directory_id: UUID | None,
    name: str,
    size: int,
    mime_type: str | None,
    checksum: str | None,
    path: str,
    telegram_channel_id: int,
    telegram_message_id: int,
) -> Node:
    """Save file record as a node"""

    node = Node(
        user_id=user_id,
        parent_id=directory_id,
        name=name,
        kind="file",
        path=path,
        depth=len([p for p in path.split("/") if p]),
        size_bytes=size,
        mime_type=mime_type,
        checksum=checksum,
        telegram_channel_id=telegram_channel_id,
        telegram_message_id=telegram_message_id,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def list_directory_entities(db: AsyncSession, user_id: UUID, path: str):
    """Return dict of children directories and files under given path."""
    path = _normalize_path(path)

    # Get direct children by parent_id
    if path == "/":
        parent_id = None
    else:
        # Find the parent directory
        res = await db.execute(
            select(Node).where(
                Node.user_id == user_id,
                Node.kind == "folder",
                Node.path == path,
                Node.deleted_at.is_(None)
            ).limit(1)
        )
        parent = res.scalar_one_or_none()
        parent_id = parent.id if parent else None

    # Get direct children
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.parent_id == parent_id,
            Node.deleted_at.is_(None)
        ).order_by(
            Node.kind.desc(),  # folders first
            Node.sort_key,
            Node.name
        )
    )
    nodes = res.scalars().all()

    directories = []
    files = []

    for node in nodes:
        if node.kind == "folder":
            directories.append({
                "name": node.name,
                "path": node.path
            })
        else:
            files.append({
                "id": str(node.id),
                "name": node.name,
                "size": node.size_bytes,
                "mime_type": node.mime_type,
                "path": node.path,
                "created_at": node.created_at.isoformat(),
            })
    
    return {"directories": directories, "files": files}


async def find_file_by_checksum(db: AsyncSession, user_id: UUID, checksum: str) -> Node | None:
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.kind == "file",
            Node.checksum == checksum,
            Node.deleted_at.is_(None)
        ).limit(1)
    )
    return res.scalar_one_or_none()


async def get_file_by_path(db: AsyncSession, user_id: UUID, path: str) -> Node | None:
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.kind == "file",
            Node.path == path,
            Node.deleted_at.is_(None)
        ).limit(1)
    )
    return res.scalar_one_or_none()


async def delete_file_record(db: AsyncSession, user_id: UUID, file_id: str) -> bool:
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        return False
        
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.id == file_uuid,
            Node.kind == "file",
            Node.deleted_at.is_(None)
        ).limit(1)
    )
    node = res.scalar_one_or_none()
    if not node:
        return False
    
    # Soft delete
    from datetime import datetime
    node.deleted_at = datetime.utcnow()
    await db.commit()
    return True


async def move_rename_file(
    db: AsyncSession,
    *,
    user_id: UUID,
    file_id: str,
    new_name: str | None,
    new_dir_path: str | None,
) -> Node | None:
    try:
        file_uuid = UUID(file_id)
    except ValueError:
        return None
        
    res = await db.execute(
        select(Node).where(
            Node.user_id == user_id,
            Node.id == file_uuid,
            Node.kind == "file",
            Node.deleted_at.is_(None)
        ).limit(1)
    )
    node = res.scalar_one_or_none()
    if not node:
        return None

    # Update name if requested
    if new_name is not None:
        node.name = new_name

    # Update directory if requested
    if new_dir_path is not None:
        new_dir_path = _normalize_path(new_dir_path)
        new_parent_id = await ensure_directory(db, user_id, new_dir_path)
        node.parent_id = new_parent_id

        # Update path
        new_path = new_dir_path + "/" + node.name if new_dir_path != "/" else "/" + node.name
        node.path = new_path
        node.depth = len([p for p in new_path.split("/") if p])

    await db.commit()
    await db.refresh(node)
    return node
