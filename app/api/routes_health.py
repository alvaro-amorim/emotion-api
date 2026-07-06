from pathlib import Path
import shutil
import sys

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.schemas import HealthResponse, SystemStatusResponse
from app.core.config import get_settings
from app.db.repository import count_audio_analyses, count_learning_examples
from app.db.session import get_session

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        python_version=sys.version.split()[0],
        transcription_engine=settings.local_transcription_engine,
        whisper_model_size=settings.whisper_model_size,
        emotion_provider=settings.emotion_analysis_provider,
        cohere_enabled=settings.external_ai_available,
        database_url=_safe_database_url(settings.database_url),
        storage_dirs=_storage_dirs(),
    )


@router.get("/v1/system/status", response_model=SystemStatusResponse)
def system_status(session: Session = Depends(get_session)) -> SystemStatusResponse:
    settings = get_settings()
    return SystemStatusResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        python_version=sys.version.split()[0],
        transcription_engine=settings.local_transcription_engine,
        whisper_model_size=settings.whisper_model_size,
        emotion_provider=settings.emotion_analysis_provider,
        cohere_enabled=settings.external_ai_available,
        cohere_configured=bool(settings.cohere_api_key.strip()),
        database_url=_safe_database_url(settings.database_url),
        storage_dirs=_storage_dirs(),
        ffmpeg_available=shutil.which("ffmpeg") is not None,
        database_exists=_sqlite_database_exists(settings.database_url),
        analyses_count=count_audio_analyses(session),
        learning_examples_count=count_learning_examples(session),
    )


def _storage_dirs() -> dict[str, str]:
    settings = get_settings()
    return {
        "storage": str(Path(settings.storage_dir)),
        "audio": str(Path(settings.audio_storage_dir)),
        "processed": str(Path(settings.processed_audio_dir)),
        "exports": str(Path(settings.exports_dir)),
    }


def _safe_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite:///"):
        database_path = database_url.removeprefix("sqlite:///")
        if database_path == ":memory:":
            return "sqlite:///:memory:"
        return f"sqlite:///{Path(database_path).name}"
    if "://" not in database_url:
        return "<configured>"
    scheme, rest = database_url.split("://", 1)
    if "@" not in rest:
        return f"{scheme}://{rest}"
    host_part = rest.split("@", 1)[1]
    return f"{scheme}://***:***@{host_part}"


def _sqlite_database_exists(database_url: str) -> bool:
    if not database_url.startswith("sqlite:///"):
        return False
    database_path = database_url.removeprefix("sqlite:///")
    if database_path == ":memory:":
        return True
    return Path(database_path).exists()
