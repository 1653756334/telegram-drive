"""File management API routes."""

import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.schemas.file import (
    DirectoryListResponse,
    UploadResponse,
    MoveRequest,
    MoveResponse,
    DeleteResponse
)
from ....application.schemas.common import SuccessResponse
from ....application.use_cases import FileUseCases, ChannelUseCases
from ....infrastructure.database.repositories import UserRepositoryImpl, NodeRepositoryImpl, ChannelRepositoryImpl
from ....infrastructure.telegram.client import telegram_client_manager
from ....infrastructure.telegram.manager import TelegramManager
from ....core.dependencies import get_db, verify_api_auth
from ....core.exceptions import NotFoundError, ValidationError, StorageError, ConflictError

router = APIRouter()


def get_file_use_cases(db: AsyncSession = Depends(get_db)) -> FileUseCases:
    """Get file use cases with dependencies."""
    user_repository = UserRepositoryImpl(db)
    node_repository = NodeRepositoryImpl(db)
    channel_repository = ChannelRepositoryImpl(db)
    telegram_manager = TelegramManager(telegram_client_manager)

    return FileUseCases(
        user_repository=user_repository,
        node_repository=node_repository,
        channel_repository=channel_repository,
        telegram_manager=telegram_manager
    )


def get_channel_use_cases(db: AsyncSession = Depends(get_db)) -> ChannelUseCases:
    """Get channel use cases with dependencies."""
    user_repository = UserRepositoryImpl(db)
    channel_repository = ChannelRepositoryImpl(db)
    telegram_manager = TelegramManager(telegram_client_manager)

    return ChannelUseCases(
        user_repository=user_repository,
        channel_repository=channel_repository,
        telegram_manager=telegram_manager
    )


@router.get("/", response_model=DirectoryListResponse)
async def list_directory(
    path: str = Query("/", description="Directory path to list"),
    file_use_cases: FileUseCases = Depends(get_file_use_cases),
    _: None = Depends(verify_api_auth)
):
    """List files and directories in specified path."""
    try:
        result = await file_use_cases.list_directory(path)
        return DirectoryListResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    path: str = Query(..., description="Upload path"),
    file: UploadFile = File(...),
    file_use_cases: FileUseCases = Depends(get_file_use_cases),
    channel_use_cases: ChannelUseCases = Depends(get_channel_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Upload a file to specified path."""
    try:
        # Ensure storage channel exists
        await channel_use_cases.ensure_storage_channel()

        # Upload file
        result = await file_use_cases.upload_file(path, file)
        return UploadResponse(**result)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/id/{file_id}/download")
async def download_file(
    file_id: str,
    file_use_cases: FileUseCases = Depends(get_file_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Download file by ID."""
    try:
        file_data, filename = await file_use_cases.download_file(file_id)

        # Build RFC 5987 compatible header
        from urllib.parse import quote
        ascii_fallback = filename.encode('latin-1', errors='ignore').decode('latin-1') or 'download.bin'
        filename_star = quote(filename, safe='')

        headers = {
            "Content-Disposition": f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{filename_star}"
        }

        def generate():
            yield file_data

        return StreamingResponse(
            generate(),
            media_type="application/octet-stream",
            headers=headers
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/id/{file_id}/move", response_model=MoveResponse)
async def move_file(
    file_id: str,
    request: MoveRequest,
    file_use_cases: FileUseCases = Depends(get_file_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Move or rename file."""
    try:
        result = await file_use_cases.move_file(
            file_id=file_id,
            new_name=request.new_name,
            new_dir_path=request.new_dir_path
        )
        return MoveResponse(**result)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/id/{file_id}", response_model=DeleteResponse)
async def delete_file(
    file_id: str,
    file_use_cases: FileUseCases = Depends(get_file_use_cases),
    _: None = Depends(verify_api_auth)
):
    """Delete file by ID."""
    try:
        success = await file_use_cases.delete_file(file_id)
        return DeleteResponse(
            success=success,
            message="File deleted successfully" if success else "File deletion failed"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
