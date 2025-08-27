from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .telegram import telegram_manager
from .routes_auth import router as auth_router
from .routes_files import router as files_router
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start telegram clients on startup
    await telegram_manager.start()
    try:
        yield
    finally:
        # Stop telegram clients on shutdown
        await telegram_manager.stop()


app = FastAPI(title="Telegram Drive", version="0.1.0", lifespan=lifespan)

# Enable permissive CORS for local dev and static file origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_token_middleware(request: Request, call_next):
    settings = get_settings()
    if settings.api_token:
        # Skip auth for health and auth endpoints
        path = request.url.path
        if not (path.startswith("/health") or path.startswith("/auth/telegram")):
            auth = request.headers.get("Authorization", "")
            if not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != settings.api_token:
                raise HTTPException(status_code=401, detail="Unauthorized")
    return await call_next(request)


app.include_router(auth_router)
app.include_router(files_router)


@app.get("/health")
async def health():
    clients = await telegram_manager.start()
    return {
        "status": "ok",
        "bot": bool(clients.bot.is_initialized),
        "user": bool(clients.user.is_initialized) if clients.user else False,
    }

