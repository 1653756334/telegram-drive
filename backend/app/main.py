"""Modern Telegram Drive Backend - Main Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings, get_database
from .config.logging import setup_logging, get_logger
from .presentation.api.v1 import auth, files
from .core.exceptions import TelegramDriveException
from .presentation.middleware.exception_handler import add_exception_handlers
from .presentation.middleware.request_logging import add_request_logging_middleware

# Initialize logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Telegram Drive Backend v2.0")
    settings = get_settings()
    logger.info(f"Log level set to: {settings.log_level}")

    db_manager = get_database()
    db_manager.initialize(settings.database_url)
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")
    await db_manager.close()
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    # Enable docs in development (when log level is DEBUG)
    enable_docs = settings.log_level == "DEBUG"

    app = FastAPI(
        title="Telegram Drive API",
        description="Modern file storage system using Telegram as backend",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if enable_docs else None,
        redoc_url="/redoc" if enable_docs else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add middleware
    add_request_logging_middleware(app)
    add_exception_handlers(app)

    # API routes
    from .presentation.api.v1 import channels, admin, telegram
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
    app.include_router(channels.router, prefix="/api/v1/channels", tags=["Channels"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(telegram.router, prefix="/api/v1/telegram", tags=["Telegram"])
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime, timezone
        from . import __version__

        return {
            "status": "healthy",
            "version": __version__,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    return app


# Create application instance
app = create_app()
