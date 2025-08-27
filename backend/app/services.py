from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pyrogram.client import Client
from pyrogram.types import ChatPrivileges
from pyrogram.errors import UserRestricted

from .models import User, TelegramSession, TelegramChannel
from .config import get_settings
from .security import decrypt
from .telegram import telegram_manager


async def get_single_user(db: AsyncSession) -> User | None:
    res = await db.execute(select(User).limit(1))
    return res.scalar_one_or_none()


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
    """Ensure storage channel exists. Return channel ID."""
    # First check if we already have a channel in database
    existing_channel_info = await get_storage_channel_info(db)
    if existing_channel_info:
        return existing_channel_info[0]  # Return existing channel ID

    # Check if we have a channel configured
    settings = get_settings()

    # Priority: username > channel_id
    if settings.storage_channel_username:
        channel_identifier = settings.storage_channel_username.strip()
        if not channel_identifier.startswith('@'):
            channel_identifier = '@' + channel_identifier

        # Resolve username to channel ID using bot
        clients = await telegram_manager.start()
        try:
            chat = await clients.bot.get_chat(channel_identifier)
            resolved_channel_id = chat.id
            resolved_title = getattr(chat, 'title', 'Unknown')
            print(f"DEBUG: Resolved channel username {channel_identifier} to ID {resolved_channel_id}")
        except Exception as e:
            raise RuntimeError(f"Cannot resolve channel username {channel_identifier}: {e}")

        # Save both username and resolved ID (only if not exists)
        from .services_nodes import get_or_create_single_user
        user_row = await get_or_create_single_user(db)

        # Double-check to avoid race condition
        existing = await db.execute(
            select(TelegramChannel).where(
                TelegramChannel.user_id == user_row.id,
                TelegramChannel.channel_id == resolved_channel_id
            ).limit(1)
        )
        if not existing.scalar_one_or_none():
            db.add(TelegramChannel(
                user_id=user_row.id,
                channel_id=resolved_channel_id,
                username=channel_identifier,
                title=resolved_title
            ))
            await db.commit()

        return resolved_channel_id
    elif settings.storage_channel_id:
        channel_identifier = settings.storage_channel_id
        if isinstance(channel_identifier, str):
            try:
                channel_identifier = int(channel_identifier)
            except ValueError:
                raise RuntimeError(f"Invalid channel ID format: {channel_identifier}")

        # Save only channel ID (only if not exists)
        from .services_nodes import get_or_create_single_user
        user_row = await get_or_create_single_user(db)

        # Double-check to avoid race condition
        existing = await db.execute(
            select(TelegramChannel).where(
                TelegramChannel.user_id == user_row.id,
                TelegramChannel.channel_id == channel_identifier
            ).limit(1)
        )
        if not existing.scalar_one_or_none():
            db.add(TelegramChannel(user_id=user_row.id, channel_id=channel_identifier, title="Preconfigured"))
            await db.commit()

        return channel_identifier

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

    # Promote bot to admin with necessary permissions
    privileges = ChatPrivileges(
        can_manage_chat=True,
        can_delete_messages=True,
        can_manage_video_chats=False,
        can_restrict_members=False,
        can_promote_members=False,
        can_change_info=False,
        can_invite_users=False,
        can_post_messages=True,
        can_edit_messages=True,
        can_pin_messages=False,
        is_anonymous=False,
    )
    await user.promote_chat_member(chat_id=channel_id, user_id=bot_username, privileges=privileges)

    # Persist channel (only if not exists)
    from .services_nodes import get_or_create_single_user
    user_row = await get_or_create_single_user(db)

    # Double-check to avoid race condition
    existing = await db.execute(
        select(TelegramChannel).where(
            TelegramChannel.user_id == user_row.id,
            TelegramChannel.channel_id == channel_id
        ).limit(1)
    )
    if not existing.scalar_one_or_none():
        db.add(TelegramChannel(user_id=user_row.id, channel_id=channel_id, title=title))
        await db.commit()

    return channel_id