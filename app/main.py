from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_audio import router as audio_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_health import router as health_router
from app.core.config import ensure_storage_directories, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.db.session import create_db_and_tables

WEB_DIR = Path(__file__).resolve().parent / "web"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    ensure_storage_directories()
    create_db_and_tables()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.app_debug,
        lifespan=lifespan,
    )
    _configure_cors(app)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(audio_router)
    app.include_router(feedback_router)
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    return app


def _configure_cors(app: FastAPI) -> None:
    settings = get_settings()
    origins = list(settings.allowed_client_origins)
    if settings.require_api_key:
        origins = [origin for origin in origins if origin != "*"]
    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", settings.api_key_header_name],
    )


app = create_app()
