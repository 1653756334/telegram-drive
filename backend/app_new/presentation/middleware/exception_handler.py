"""Global exception handlers for the application."""

import logging
from typing import Union

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ...core.exceptions import (
    TelegramDriveException,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ValidationError,
    TelegramError,
    StorageError,
    ConflictError
)

logger = logging.getLogger(__name__)


def add_exception_handlers(app: FastAPI) -> None:
    """Add global exception handlers to FastAPI app."""
    
    @app.exception_handler(TelegramDriveException)
    async def telegram_drive_exception_handler(
        request: Request, 
        exc: TelegramDriveException
    ) -> JSONResponse:
        """Handle custom application exceptions."""
        status_code = 500
        
        # Map exception types to HTTP status codes
        if isinstance(exc, AuthenticationError):
            status_code = 401
        elif isinstance(exc, AuthorizationError):
            status_code = 403
        elif isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, ValidationError):
            status_code = 400
        elif isinstance(exc, ConflictError):
            status_code = 409
        elif isinstance(exc, (TelegramError, StorageError)):
            status_code = 500
        
        logger.error(f"Application error: {exc.message}", extra={
            "code": exc.code,
            "details": exc.details,
            "path": request.url.path
        })
        
        return JSONResponse(
            status_code=status_code,
            content={
                "error": exc.message,
                "code": exc.code,
                "details": exc.details
            }
        )
    
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, 
        exc: IntegrityError
    ) -> JSONResponse:
        """Handle database integrity errors."""
        logger.error(f"Database integrity error: {exc}", extra={
            "path": request.url.path
        })
        
        return JSONResponse(
            status_code=409,
            content={
                "error": "Data integrity constraint violation",
                "code": "INTEGRITY_ERROR",
                "details": {"database_error": str(exc.orig) if exc.orig else str(exc)}
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(
        request: Request, 
        exc: SQLAlchemyError
    ) -> JSONResponse:
        """Handle general SQLAlchemy errors."""
        logger.error(f"Database error: {exc}", extra={
            "path": request.url.path
        })
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Database operation failed",
                "code": "DATABASE_ERROR",
                "details": {"database_error": str(exc)}
            }
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, 
        exc: HTTPException
    ) -> JSONResponse:
        """Handle FastAPI HTTP exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "code": "HTTP_ERROR"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, 
        exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        logger.error(f"Unexpected error: {exc}", extra={
            "path": request.url.path,
            "exception_type": type(exc).__name__
        }, exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
                "details": {"exception_type": type(exc).__name__}
            }
        )
