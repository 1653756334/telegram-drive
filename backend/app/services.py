from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from pyrogram.client import Client
from pyrogram.types import ChatPrivileges
from pyrogram.errors import UserRestricted

from .models import User, TelegramSession, TelegramChannel, Directory, File
from .config import get_settings
from .security import decrypt
from .telegram import telegram_manager


async def get_single_user(db: AsyncSession) -> User | None:
    res = await db.execute(select(User).limit(1))
    return res.scalar_one_or_none()


async def get_or_create_single_user(db: AsyncSession) -> User:
    u = await get_single_user(db)
    if u:
        return u
    u = User(username=None)
    db.add(u)
    await db.flush()
    return u


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


async def ensure_storage_channel(db: AsyncSession) -> int:
    """Ensure a private channel exists for storage and bot is admin. Return channel id."""
    # If exists in DB, return it
    cid = await get_storage_channel_id(db)
    if cid:
        return cid

    settings = get_settings()

    # If env pre-configured channel exists (ID or username), resolve and persist
    channel_identifier = settings.get_storage_channel_identifier()
    if channel_identifier:
        # Need to resolve username to ID if it's a username
        if isinstance(channel_identifier, str) and channel_identifier.startswith('@'):
            # Resolve username to channel ID using bot
            clients = await telegram_manager.start()
            try:
                chat = await clients.bot.get_chat(channel_identifier)
                resolved_channel_id = chat.id
                resolved_title = getattr(chat, 'title', 'Unknown')
                print(f"DEBUG: Resolved channel username {channel_identifier} to ID {resolved_channel_id}")
            except Exception as e:
                raise RuntimeError(f"Cannot resolve channel username {channel_identifier}: {e}")

            # Save both username and resolved ID
            user_row = await get_or_create_single_user(db)
            db.add(TelegramChannel(
                user_id=user_row.id,
                channel_id=resolved_channel_id,
                username=channel_identifier,
                title=resolved_title
            ))
            await db.commit()
            return resolved_channel_id
        else:
            resolved_channel_id = channel_identifier

            # Save only channel ID
            user_row = await get_or_create_single_user(db)
            db.add(TelegramChannel(user_id=user_row.id, channel_id=resolved_channel_id, title="Preconfigured"))
            await db.commit()
            return resolved_channel_id

    # Need user session to create and manage channel
    session_string = await get_latest_session(db)
    if not session_string:
        raise RuntimeError("No user session available; login required")

    # Start user client in-memory using DB session string (no local persistence)
    await telegram_manager.ensure_user_started(session_string)
    clients = await telegram_manager.start()
    user: Client = clients.user  # type: ignore[assignment]

    # Create channel
    title = "MyDrive_Storage"
    try:
        chat = await user.create_channel(title=title, description="Storage for Telegram Drive")
    except UserRestricted:
        raise RuntimeError(
            "Your Telegram account is restricted and cannot create channels. "
            "Please create a private channel manually in Telegram, add your bot as admin, "
            "and then bind it via .env TGDRIVE_STORAGE_CHANNEL_ID or POST /channels/bind."
        )
    channel_id = chat.id

    # Add bot to channel and promote to admin
    me = await clients.bot.get_me()
    bot_username = me.username
    if not bot_username:
        raise RuntimeError("Bot username not available")

    await user.add_chat_members(chat_id=channel_id, user_ids=[bot_username])

    privileges = ChatPrivileges(
        can_change_info=True,
        can_delete_messages=True,
        can_post_messages=True,
        can_edit_messages=True,
        can_invite_users=True,
        can_restrict_members=False,
        can_pin_messages=True,
        can_manage_chat=True,
        can_promote_members=False,
        can_manage_video_chats=False,
        is_anonymous=False,
    )
    await user.promote_chat_member(chat_id=channel_id, user_id=bot_username, privileges=privileges)

    # Persist channel
    user_row = await get_or_create_single_user(db)
    db.add(TelegramChannel(user_id=user_row.id, channel_id=channel_id, title=title))
    await db.commit()

    return channel_id


def _normalize_path(path: str) -> str:
    p = (path or "/").strip()
    if not p.startswith("/"):
        p = "/" + p
    # remove trailing slash except root
    if len(p) > 1 and p.endswith("/"):
        p = p[:-1]
    return p


async def ensure_directory(db: AsyncSession, user_id: int, path: str) -> int | None:
    """Ensure directory tree exists for a logical path like '/a/b'. Return leaf directory id or None for root."""
    path = _normalize_path(path)
    if path == "/":
        return None
    parent_id: int | None = None
    # split into segments without leading slash
    segments = [seg for seg in path.split("/") if seg]
    for seg in segments:
        q = select(Directory).where(
            Directory.user_id == user_id,
            Directory.name == seg,
            Directory.parent_id == parent_id,
        ).limit(1)
        res = await db.execute(q)
        row = res.scalar_one_or_none()
        if row:
            parent_id = row.id
        else:
            d = Directory(user_id=user_id, name=seg, parent_id=parent_id)
            db.add(d)
            await db.flush()
            parent_id = d.id
    return parent_id


async def get_directory_by_path(db: AsyncSession, user_id: int, path: str) -> Directory | None:
    path = _normalize_path(path)
    if path == "/":
        return None
    parent_id: int | None = None
    dir_obj: Directory | None = None
    for seg in [seg for seg in path.split("/") if seg]:
        res = await db.execute(
            select(Directory).where(
                Directory.user_id == user_id,
                Directory.name == seg,
                Directory.parent_id == parent_id,
            ).limit(1)
        )
        dir_obj = res.scalar_one_or_none()
        if not dir_obj:
            return None
        parent_id = dir_obj.id
    return dir_obj


async def save_file_record(
    db: AsyncSession,
    *,
    user_id: int,
    directory_id: int | None,
    name: str,
    size: int,
    mime_type: str | None,
    checksum: str | None,
    path: str,
    telegram_channel_id: int,
    telegram_message_id: int,
) -> File:
    rec = File(
        user_id=user_id,
        directory_id=directory_id,
        name=name,
        size=size,
        mime_type=mime_type,
        checksum=checksum,
        path=path,
        telegram_channel_id=telegram_channel_id,
        telegram_message_id=telegram_message_id,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)
    return rec


async def list_directory_entities(db: AsyncSession, user_id: int, path: str):
    """Return dict of children directories and files under given path."""
    path = _normalize_path(path)
    # Resolve directory id
    if path == "/":
        parent_id = None
        base_path = "/"
    else:
        # walk to get directory id without creating
        parent_id = None
        for seg in [seg for seg in path.split("/") if seg]:
            q = select(Directory).where(
                Directory.user_id == user_id,
                Directory.name == seg,
                Directory.parent_id == parent_id,
            ).limit(1)
            res = await db.execute(q)
            row = res.scalar_one_or_none()
            if not row:
                # directory doesn't exist; return empty
                return {"directories": [], "files": []}
            parent_id = row.id
        base_path = path

    # children directories
    q_dirs = select(Directory).where(Directory.parent_id == parent_id, Directory.user_id == user_id)
    dirs_res = await db.execute(q_dirs)
    dirs = [
        {"name": d.name, "path": (base_path if base_path != "/" else "") + "/" + d.name}
        for d in dirs_res.scalars().all()
    ]

    # files: those whose directory_id == parent_id
    q_files = select(File).where(File.user_id == user_id, File.directory_id == parent_id)
    files_res = await db.execute(q_files)
    files = [
        {
            "id": f.id,
            "name": f.name,
            "size": f.size,
            "mime_type": f.mime_type,
            "path": f.path,
            "created_at": f.created_at.isoformat(),
        }
        for f in files_res.scalars().all()
    ]

    return {"directories": dirs, "files": files}


async def find_file_by_checksum(db: AsyncSession, user_id: int, checksum: str) -> File | None:
    res = await db.execute(select(File).where(File.user_id == user_id, File.checksum == checksum).limit(1))
    return res.scalar_one_or_none()


async def get_file_by_path(db: AsyncSession, user_id: int, path: str) -> File | None:
    res = await db.execute(select(File).where(File.user_id == user_id, File.path == path).limit(1))
    return res.scalar_one_or_none()


async def delete_file_record(db: AsyncSession, user_id: int, file_id: int) -> bool:
    res = await db.execute(select(File).where(File.user_id == user_id, File.id == file_id).limit(1))
    f = res.scalar_one_or_none()
    if not f:
        return False
    await db.execute(delete(File).where(File.id == file_id))
    await db.commit()
    return True


async def move_rename_file(
    db: AsyncSession,
    *,
    user_id: int,
    file_id: int,
    new_name: str | None,
    new_dir_path: str | None,
) -> File | None:
    res = await db.execute(select(File).where(File.user_id == user_id, File.id == file_id).limit(1))
    f = res.scalar_one_or_none()
    if not f:
        return None

    # Update directory if requested
    if new_dir_path is not None:
        dir_id = await ensure_directory(db, user_id, new_dir_path)
        f.directory_id = dir_id
        base_path = _normalize_path(new_dir_path)
    else:
        # keep current directory
        # Need to derive directory path from f.path
        # f.path is full path like /a/b/file
        parts = f.path.rsplit("/", 1)
        base_path = parts[0] if len(parts) == 2 and parts[0] else "/"

    # Update name if requested
    if new_name is not None:
        f.name = new_name

    # Update full path
    f.path = (base_path if base_path != "/" else "") + "/" + f.name

    await db.commit()
    await db.refresh(f)
    return f


async def delete_directory_if_empty(db: AsyncSession, user_id: int, path: str) -> bool:
    d = await get_directory_by_path(db, user_id, path)
    if not d:
        return False
    # has child directories?
    child_dir = await db.execute(select(Directory).where(Directory.parent_id == d.id).limit(1))
    if child_dir.scalar_one_or_none():
        return False
    # has files?
    files = await db.execute(select(File).where(File.user_id == user_id, File.directory_id == d.id).limit(1))
    if files.scalar_one_or_none():
        return False
    await db.execute(delete(Directory).where(Directory.id == d.id))
    await db.commit()
    return True


async def rename_directory(db: AsyncSession, user_id: int, path: str, new_name: str) -> bool:
    d = await get_directory_by_path(db, user_id, path)
    if not d:
        return False
    # compute old and new base path
    base_parts = _normalize_path(path).rsplit("/", 1)
    parent_path = base_parts[0] if len(base_parts) == 2 and base_parts[0] else "/"
    old_prefix = (parent_path if parent_path != "/" else "") + "/" + d.name
    new_prefix = (parent_path if parent_path != "/" else "") + "/" + new_name

    # Update directory name
    d.name = new_name

    # Update all files path under subtree: those whose path == old_prefix/file or startswith old_prefix + '/'
    like1 = old_prefix + "/%"
    files_res = await db.execute(select(File).where(File.user_id == user_id, (File.path == old_prefix) | (File.path.like(like1))))
    files = files_res.scalars().all()
    for f in files:
        if f.path == old_prefix:
            f.path = new_prefix
        elif f.path.startswith(old_prefix + "/"):
            f.path = new_prefix + f.path[len(old_prefix):]

    await db.commit()
    return True
