"""Modern Telegram Drive Backend - Main Application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings, get_database
from .presentation.api.v1 import auth, files
from .core.exceptions import TelegramDriveException
from .presentation.middleware.exception_handler import add_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    settings = get_settings()
    db_manager = get_database()
    db_manager.initialize(settings.database_url)
    
    yield
    
    # Shutdown
    await db_manager.close()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title="Telegram Drive API",
        description="Modern file storage system using Telegram as backend",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Exception handlers
    add_exception_handlers(app)
    
    # API routes
    from .presentation.api.v1 import channels
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
    app.include_router(channels.router, prefix="/api/v1/channels", tags=["Channels"])
    
    # Health check
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime
        from . import __version__
        
        return {
            "status": "healthy",
            "version": __version__,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return app


# Create application instance
app = create_app()
