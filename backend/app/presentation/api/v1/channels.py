"""Channel management API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.schemas.common import SuccessResponse
from ....application.use_cases import ChannelUseCases
from ....infrastructure.database.repositories import UserRepositoryImpl, ChannelRepositoryImpl
from ....infrastructure.telegram.client import telegram_client_manager
from ....infrastructure.telegram.manager import TelegramManager
from ....core.dependencies import get_db
from ....core.exceptions import NotFoundError, ValidationError, TelegramError, ConflictError

router = APIRouter()


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


@router.post("/ensure", response_model=SuccessResponse)
async def ensure_storage_channel(
    channel_use_cases: ChannelUseCases = Depends(get_channel_use_cases)
):
    """Ensure storage channel exists."""
    try:
        result = await channel_use_cases.ensure_storage_channel()
        return SuccessResponse(
            message="Storage channel ensured",
            data=result
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_channels(
    channel_use_cases: ChannelUseCases = Depends(get_channel_use_cases)
):
    """List all channels for current user."""
    try:
        channels = await channel_use_cases.list_channels()
        return {"channels": channels}
    except TelegramError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=SuccessResponse)
async def add_channel(
    identifier: str = Query(..., description="Channel ID or username"),
    title: str = Query(None, description="Optional channel title"),
    channel_use_cases: ChannelUseCases = Depends(get_channel_use_cases)
):
    """Add a new channel."""
    try:
        # Try to parse as integer (channel ID)
        try:
            channel_id = int(identifier)
            result = await channel_use_cases.add_channel(channel_id, title)
        except ValueError:
            # Treat as username
            result = await channel_use_cases.add_channel(identifier, title)
        
        return SuccessResponse(
            message="Channel added successfully",
            data=result
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{channel_id}", response_model=SuccessResponse)
async def remove_channel(
    channel_id: int,
    channel_use_cases: ChannelUseCases = Depends(get_channel_use_cases)
):
    """Remove a channel."""
    try:
        success = await channel_use_cases.remove_channel(channel_id)
        return SuccessResponse(
            message="Channel removed successfully" if success else "Channel removal failed"
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except TelegramError as e:
        raise HTTPException(status_code=500, detail=str(e))
