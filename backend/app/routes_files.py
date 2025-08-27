from __future__ import annotations

import json
import os
import io
import tempfile
import mimetypes
import hashlib
import subprocess
from urllib.parse import quote
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from pyrogram.client import Client

from .telegram import telegram_manager
from .config import get_settings
from .db import get_db
from .services import (
    get_latest_session,
    ensure_storage_channel,
    ensure_directory,
    get_or_create_single_user,
    save_file_record,
    list_directory_entities,
    find_file_by_checksum,
    delete_file_record,
    move_rename_file,
)

router = APIRouter(prefix="/files", tags=["files"])


def _calc_checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_video_metadata(video_path: str) -> dict:
    """Extract video metadata using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            print(f"DEBUG: ffprobe failed: {result.stderr}")
            return {}

        data = json.loads(result.stdout)
        video_stream = None

        # Find the first video stream
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                video_stream = stream
                break

        if not video_stream:
            return {}

        # Extract metadata
        duration = float(data.get('format', {}).get('duration', 0))
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))

        return {
            'duration': int(duration),
            'width': width,
            'height': height,
        }
    except Exception as e:
        print(f"DEBUG: Video metadata extraction failed: {e}")
        return {}


def _generate_video_thumbnail(video_path: str) -> str | None:
    """Generate video thumbnail using ffmpeg"""
    try:
        thumb_path = video_path + "_thumb.jpg"
        cmd = [
            'ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1',
            '-f', 'image2', '-y', thumb_path
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode == 0 and os.path.exists(thumb_path):
            return thumb_path
        else:
            print(f"DEBUG: Thumbnail generation failed: {result.stderr}")
            return None
    except Exception as e:
        print(f"DEBUG: Thumbnail generation error: {e}")
        return None


@router.post("")
async def upload(path: str, upload: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    clients = await telegram_manager.start()

    # Ensure storage channel exists (will require user session once)
    try:
        channel_id = await ensure_storage_channel(db)
    except RuntimeError as e:
        # allow small files via bot if pre-configured channel id exists in env
        if settings.storage_channel_id:
            channel_id = settings.storage_channel_id
        else:
            raise HTTPException(status_code=400, detail=str(e))

    # Persist to a temporary file path; Pyrogram handles file paths robustly
    filename = upload.filename or "upload.bin"
    suffix = os.path.splitext(filename)[1] or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)

    try:
        size = os.path.getsize(temp_path)
        checksum = _calc_checksum(temp_path)

        # 规范化目录路径并构造文件完整路径（用于唯一约束 user_id+path）
        def _normalize_dir(p: str) -> str:
            p = (p or "/").strip()
            if not p.startswith("/"):
                p = "/" + p
            if len(p) > 1 and p.endswith("/"):
                p = p[:-1]
            return p
        base_path = _normalize_dir(path)
        full_path = (base_path if base_path != "/" else "") + "/" + filename

        # 秒传：查找同一用户下是否已有相同 checksum
        user_row = await get_or_create_single_user(db)

        # 先检查同路径是否已有文件，避免触发唯一约束
        from .services import get_file_by_path
        existing_same_path = await get_file_by_path(db, user_row.id, full_path)
        if existing_same_path:
            if existing_same_path.checksum == checksum:
                return {"file_id": existing_same_path.id, "message_id": existing_same_path.telegram_message_id, "via": "exists"}
            # 同路径有不同内容
            raise HTTPException(status_code=409, detail={
                "code": "FILE_ALREADY_EXISTS",
                "message": "File with same path already exists",
                "path": full_path,
            })

        existing = await find_file_by_checksum(db, user_row.id, checksum)
        if existing:
            # 只在 DB 写一条指向已有内容的“硬链接式”记录：引用同一 message
            directory_id = await ensure_directory(db, user_row.id, base_path)
            rec = await save_file_record(
                db,
                user_id=user_row.id,
                directory_id=directory_id,
                name=filename,
                size=existing.size,
                mime_type=upload.content_type or mimetypes.guess_type(filename)[0],
                checksum=checksum,
                path=full_path,
                telegram_channel_id=existing.telegram_channel_id,
                telegram_message_id=existing.telegram_message_id,
            )
            return {"file_id": rec.id, "message_id": existing.telegram_message_id, "via": "instant"}

        caption = json.dumps({"path": base_path, "name": filename, "size": size, "checksum": checksum})

        # Determine file type for better Telegram preview
        mime_type = upload.content_type or mimetypes.guess_type(filename)[0] or ""
        is_image = mime_type.startswith('image/')
        is_video = mime_type.startswith('video/')
        is_audio = mime_type.startswith('audio/')

        msg = None
        if size <= 50 * 1024 * 1024:  # <= 50MB use bot
            bot: Client = clients.bot
            if is_image:
                msg = await bot.send_photo(chat_id=channel_id, photo=temp_path, caption=caption)
            elif is_video:
                # Extract video metadata for better preview
                video_meta = _extract_video_metadata(temp_path)
                thumb_path = _generate_video_thumbnail(temp_path)

                try:
                    # Only pass metadata if we have valid values
                    video_kwargs = {
                        'chat_id': channel_id,
                        'video': temp_path,
                        'caption': caption,
                    }

                    if video_meta.get('duration'):
                        video_kwargs['duration'] = video_meta['duration']
                    if video_meta.get('width'):
                        video_kwargs['width'] = video_meta['width']
                    if video_meta.get('height'):
                        video_kwargs['height'] = video_meta['height']
                    if thumb_path:
                        video_kwargs['thumb'] = thumb_path

                    msg = await bot.send_video(**video_kwargs)
                finally:
                    # Clean up thumbnail
                    if thumb_path and os.path.exists(thumb_path):
                        try:
                            os.remove(thumb_path)
                        except Exception:
                            pass
            elif is_audio:
                msg = await bot.send_audio(chat_id=channel_id, audio=temp_path, caption=caption)
            else:
                msg = await bot.send_document(chat_id=channel_id, document=temp_path, file_name=filename, caption=caption)
            via = "bot"
        else:
            # large file: create independent user client to avoid conflicts with bot
            session_string = await get_latest_session(db)
            if not session_string:
                raise HTTPException(status_code=400, detail="User session not available for large upload")

            # Create independent user client (not managed by telegram_manager)
            settings = get_settings()
            user = Client(
                name="tgdrive-upload-user",
                api_id=settings.api_id,
                api_hash=settings.api_hash,
                session_string=session_string,
                in_memory=True,
            )

            try:
                await user.start()
                print("DEBUG: Independent user client started successfully")

                # Get user info for debugging
                try:
                    me = await user.get_me()
                    print(f"DEBUG: Current user - ID: {me.id}, Username: {me.username}, Phone: {me.phone_number}, First Name: {me.first_name}")
                except Exception as e:
                    print(f"DEBUG: Cannot get user info: {e}")
                    me = None

                # Test channel access before attempting to send document
                # Try multiple methods to ensure channel is accessible
                chat_info = None
                for attempt in range(3):
                    try:
                        print(f"DEBUG: Attempt {attempt + 1} to access channel {channel_id}")

                        # Try both numeric ID and potential username
                        chat_info = None
                        settings = get_settings()

                        # First try the numeric ID
                        try:
                            chat_info = await user.get_chat(channel_id)
                            print(f"DEBUG: Numeric ID {channel_id} worked")
                        except Exception as id_error:
                            print(f"DEBUG: Numeric ID {channel_id} failed: {id_error}")

                            # Try username from database first, then from config
                            from .services import get_storage_channel_info
                            channel_info = await get_storage_channel_info(db)
                            username_to_try = None

                            if channel_info and channel_info[1]:  # Has username in DB
                                username_to_try = channel_info[1]
                                print(f"DEBUG: Using username from database: {username_to_try}")
                            elif settings.storage_channel_username:  # Has username in config
                                username = settings.storage_channel_username.strip()
                                if not username.startswith('@'):
                                    username = '@' + username
                                username_to_try = username
                                print(f"DEBUG: Using username from config: {username_to_try}")

                            if username_to_try:
                                try:
                                    print(f"DEBUG: Trying username {username_to_try}")
                                    chat_info = await user.get_chat(username_to_try)
                                    print(f"DEBUG: Username {username_to_try} worked")
                                except Exception as username_error:
                                    print(f"DEBUG: Username {username_to_try} also failed: {username_error}")

                        if chat_info:
                            print(f"DEBUG: User can access channel, title: {chat_info.title}, type: {chat_info.type}")
                        else:
                            raise Exception(f"Cannot access channel {channel_id} or username")

                        # Try to get user's status in the channel
                        if me:
                            try:
                                member = await user.get_chat_member(channel_id, me.id)
                                print(f"DEBUG: User status in channel: {member.status}")
                            except Exception as member_e:
                                print(f"DEBUG: Cannot get user status in channel: {member_e}")
                        break  # Success, exit retry loop
                    except Exception as e:
                        print(f"DEBUG: Attempt {attempt + 1} failed to access channel {channel_id}, error: {e}")
                        if attempt < 2:  # Not the last attempt
                            print(f"DEBUG: Retrying in 3 seconds... (attempt {attempt + 1}/3)")
                            import asyncio
                            await asyncio.sleep(3)
                        else:
                            # Last attempt failed - this is a fundamental issue
                            print(f"DEBUG: CRITICAL - User cannot access channel {channel_id}")
                            print(f"DEBUG: User ID: {me.id if me else 'unknown'}")
                            print(f"DEBUG: Username: {me.username if me else 'unknown'}")
                            print(f"DEBUG: Phone: {me.phone_number if me else 'unknown'}")
                            print(f"DEBUG: This suggests either:")
                            print(f"DEBUG: 1. Channel ID {channel_id} is incorrect")
                            print(f"DEBUG: 2. User {me.id if me else 'unknown'} is not a member of this channel")
                            print(f"DEBUG: 3. Channel was deleted or user was removed")
                            print(f"DEBUG: 4. There's a Pyrogram session/cache issue")

                            # Try one more diagnostic: check if we can get any chats at all
                            try:
                                print("DEBUG: Testing if user can get any chats...")
                                me_again = await user.get_me()
                                print(f"DEBUG: get_me() works: {me_again.id}")
                            except Exception as me_e:
                                print(f"DEBUG: Even get_me() fails: {me_e}")

                            raise HTTPException(status_code=400, detail={
                                "code": "CHANNEL_NOT_ACCESSIBLE",
                                "message": f"User account (ID: {me.id if me else 'unknown'}) cannot access channel {channel_id}. Please verify: 1) Channel ID is correct, 2) User is a member/admin of the channel, 3) Channel still exists and is accessible.",
                                "channel_id": channel_id,
                                "user_id": me.id if me else None,
                                "username": me.username if me else None,
                                "phone": me.phone_number if me else None,
                            }) from e

                try:
                    if is_image:
                        msg = await user.send_photo(chat_id=channel_id, photo=temp_path, caption=caption)
                    elif is_video:
                        # Extract video metadata for better preview
                        video_meta = _extract_video_metadata(temp_path)
                        thumb_path = _generate_video_thumbnail(temp_path)

                        try:
                            # Only pass metadata if we have valid values
                            video_kwargs = {
                                'chat_id': channel_id,
                                'video': temp_path,
                                'caption': caption,
                            }

                            if video_meta.get('duration'):
                                video_kwargs['duration'] = video_meta['duration']
                            if video_meta.get('width'):
                                video_kwargs['width'] = video_meta['width']
                            if video_meta.get('height'):
                                video_kwargs['height'] = video_meta['height']
                            if thumb_path:
                                video_kwargs['thumb'] = thumb_path

                            msg = await user.send_video(**video_kwargs)
                        finally:
                            # Clean up thumbnail
                            if thumb_path and os.path.exists(thumb_path):
                                try:
                                    os.remove(thumb_path)
                                except Exception:
                                    pass
                    elif is_audio:
                        msg = await user.send_audio(chat_id=channel_id, audio=temp_path, caption=caption)
                    else:
                        msg = await user.send_document(chat_id=channel_id, document=temp_path, file_name=filename, caption=caption)
                except Exception as e:
                    raise HTTPException(status_code=400, detail={
                        "code": "DOCUMENT_SEND_FAILED",
                        "message": f"Failed to send document via user client: {str(e)}",
                        "channel_id": channel_id,
                    }) from e
                via = "user"

            finally:
                # Always clean up the independent user client
                try:
                    await user.stop()
                    print("DEBUG: Independent user client stopped")
                except Exception as e:
                    print(f"DEBUG: Error stopping user client: {e}")

        if msg is None:
            raise HTTPException(status_code=500, detail="Upload failed: no message returned")

        # Save record into DB (directory tree + file record)
        directory_id = await ensure_directory(db, user_row.id, base_path)
        mime_type = upload.content_type or mimetypes.guess_type(filename)[0]
        rec = await save_file_record(
            db,
            user_id=user_row.id,
            directory_id=directory_id,
            name=filename,
            size=size,
            mime_type=mime_type,
            checksum=checksum,
            path=full_path,
            telegram_channel_id=channel_id,
            telegram_message_id=int(msg.id),
        )

        return {"file_id": rec.id, "message_id": int(msg.id), "via": via}
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


def _to_bytes(data: object) -> bytes:
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, io.BytesIO):
        return data.getvalue()
    if isinstance(data, str) and os.path.exists(data):
        with open(data, "rb") as f:
            return f.read()
    raise TypeError("Unexpected download type")


@router.get("")
async def list_entries(path: str = Query("/"), db: AsyncSession = Depends(get_db)):
    user_row = await get_or_create_single_user(db)
    return await list_directory_entities(db, user_row.id, path)


async def _try_download_with_client(client, channel_identifier, message_id):
    """Helper function to download file with given client and channel identifier"""
    try:
        print(f"DEBUG: Trying to download with channel identifier: {channel_identifier}")
        msg_obj = await client.get_messages(chat_id=channel_identifier, message_ids=message_id)
        if isinstance(msg_obj, list):
            msg_obj = msg_obj[0]
        data = await client.download_media(msg_obj, in_memory=True)
        return _to_bytes(data)
    except Exception as e:
        print(f"DEBUG: Download failed with {channel_identifier}: {e}")
        return None


async def _get_channel_identifiers(db: AsyncSession):
    """Get all possible channel identifiers (ID and usernames)"""
    identifiers = []

    # Get from database
    from .services import get_storage_channel_info
    channel_info = await get_storage_channel_info(db)
    if channel_info:
        # Add channel ID
        identifiers.append(channel_info[0])
        # Add username if available
        if channel_info[1]:
            identifiers.append(channel_info[1])

    # Add from config if not already included
    settings = get_settings()
    if settings.storage_channel_username:
        username = settings.storage_channel_username.strip()
        if not username.startswith('@'):
            username = '@' + username
        if username not in identifiers:
            identifiers.append(username)

    return identifiers


async def _download_with_bot(file_record, db: AsyncSession):
    """Try downloading with bot client using all available channel identifiers"""
    clients = await telegram_manager.start()
    identifiers = await _get_channel_identifiers(db)

    for identifier in identifiers:
        print(f"DEBUG: Bot trying identifier: {identifier}")
        raw = await _try_download_with_client(clients.bot, identifier, file_record.telegram_message_id)
        if raw:
            return raw
    return None


async def _download_with_user(file_record, db: AsyncSession):
    """Try downloading with independent user client using all available channel identifiers"""
    session_string = await get_latest_session(db)
    if not session_string:
        return None

    settings = get_settings()
    user = Client(
        name="tgdrive-download-user",
        api_id=settings.api_id,
        api_hash=settings.api_hash,
        session_string=session_string,
        in_memory=True,
    )

    try:
        await user.start()
        print("DEBUG: Independent user client started for download")

        identifiers = await _get_channel_identifiers(db)
        for identifier in identifiers:
            print(f"DEBUG: User client trying identifier: {identifier}")
            raw = await _try_download_with_client(user, identifier, file_record.telegram_message_id)
            if raw:
                return raw
        return None

    finally:
        try:
            await user.stop()
            print("DEBUG: Independent user client stopped")
        except Exception as e:
            print(f"DEBUG: Error stopping download user client: {e}")


@router.get("/id/{file_id}/download")
async def download_by_id(file_id: int, db: AsyncSession = Depends(get_db)):
    # Locate file
    from sqlalchemy import select
    from .models import File

    res = await db.execute(select(File).where(File.id == file_id).limit(1))
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    # Try downloading with bot first, then user client
    raw = await _download_with_bot(f, db)
    if raw is None:
        raw = await _download_with_user(f, db)

    if raw is None:
        raise HTTPException(status_code=404, detail="File not found or cannot be downloaded")

    # Build RFC 5987 compatible header; include ASCII fallback for latin-1 safe
    filename = f.name or "download.bin"
    ascii_fallback = filename.encode('latin-1', errors='ignore').decode('latin-1') or 'download.bin'
    from urllib.parse import quote
    filename_star = quote(filename, safe='')
    headers = {
        "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{filename_star}"
    }
    return Response(content=raw, media_type="application/octet-stream", headers=headers)


@router.delete("/id/{file_id}")
async def delete_file(file_id: int, db: AsyncSession = Depends(get_db)):
    user_row = await get_or_create_single_user(db)
    ok = await delete_file_record(db, user_row.id, file_id)
    if not ok:
        raise HTTPException(status_code=404, detail="File not found")
    return {"ok": True}


class MoveRenamePayload(BaseModel):
    new_name: str | None = None
    new_dir_path: str | None = None


@router.post("/id/{file_id}/move")
async def move_or_rename(file_id: int, payload: MoveRenamePayload, db: AsyncSession = Depends(get_db)):
    user_row = await get_or_create_single_user(db)
    rec = await move_rename_file(
        db,
        user_id=user_row.id,
        file_id=file_id,
        new_name=payload.new_name,
        new_dir_path=payload.new_dir_path,
    )
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    return {"id": rec.id, "name": rec.name, "path": rec.path}

