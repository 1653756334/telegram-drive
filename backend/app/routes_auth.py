from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pyrogram.client import Client
from pyrogram.errors import SessionPasswordNeeded

from .schemas import SendCodeRequest, VerifyCodeRequest
from .config import get_settings
from .security import encrypt
from .db import get_db
from .models import User, TelegramSession
from .telegram import telegram_manager

router = APIRouter(prefix="/auth/telegram", tags=["auth"])

# Keep temporary login clients in-memory per phone until verification
_pending_login: dict[str, tuple[Client, str]] = {}


@router.post("/send_code")
async def send_code(payload: SendCodeRequest):
    settings = get_settings()

    # Close previous pending client for this phone, if any
    old = _pending_login.pop(payload.phone, None)
    if old is not None:
        try:
            await old[0].disconnect()
        except Exception:
            pass

    temp_client = Client(
        name=f"tgdrive-login-{payload.phone}",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        in_memory=True,
    )

    await temp_client.connect()
    sent = await temp_client.send_code(payload.phone)
    # Keep client alive and remember phone_code_hash
    _pending_login[payload.phone] = (temp_client, sent.phone_code_hash)
    return {"phone_code_hash": sent.phone_code_hash}


@router.post("/verify")
async def verify(payload: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()

    pending = _pending_login.get(payload.phone)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending login. Please send code first.")

    temp_client, phone_code_hash = pending

    try:
        try:
            await temp_client.sign_in(
                phone_number=payload.phone,
                phone_code=payload.code,
                phone_code_hash=phone_code_hash,
            )
        except SessionPasswordNeeded:
            if not payload.password:
                raise HTTPException(status_code=400, detail="Two-step verification enabled, password required")
            await temp_client.check_password(payload.password)

        session_string = await temp_client.export_session_string()
        encrypted = encrypt(session_string, settings.session_secret)

        # Get user info from Telegram
        me = await temp_client.get_me()
        telegram_username = me.username

        # Persist single-user data: create default user if not exists, store session
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            user = User(username=telegram_username)
            db.add(user)
            await db.flush()
        else:
            # Update existing user with real Telegram info
            user.username = telegram_username
            await db.flush()

        # Keep only one active session: delete old ones, then insert new
        await db.execute(TelegramSession.__table__.delete())  # type: ignore[arg-type]
        db.add(TelegramSession(user_id=user.id, session_string_encrypted=encrypted))
        await db.commit()

        # Start user client in-memory using DB session only (no local persistence)
        await telegram_manager.ensure_user_started(session_string)

        return {"session_encrypted": encrypted}
    finally:
        # Cleanup: disconnect and remove pending
        try:
            await temp_client.disconnect()
        finally:
            _pending_login.pop(payload.phone, None)
