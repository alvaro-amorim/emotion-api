from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import (
    AudioFileTooLargeError,
    EmptyAudioFileError,
    UnsupportedAudioFormatError,
)
from app.utils.audio_utils import get_file_extension
from app.utils.file_utils import sanitize_filename
from app.utils.hash_utils import create_sha256

CHUNK_SIZE = 1024 * 1024


class StoredAudio(BaseModel):
    original_file_name: str
    stored_file_name: str
    storage_path: str
    file_hash: str
    file_size_bytes: int
    extension: str


async def save_upload_file(file: UploadFile, settings: Settings | None = None) -> StoredAudio:
    settings = settings or get_settings()
    original_file_name = file.filename or ""
    extension = get_file_extension(original_file_name)

    if extension not in settings.allowed_audio_extensions:
        raise UnsupportedAudioFormatError()

    storage_dir = Path(settings.audio_storage_dir)
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = sanitize_filename(original_file_name)
    stored_file_name = f"{uuid4().hex}_{safe_name}"
    storage_path = storage_dir / stored_file_name

    hasher = create_sha256()
    total_size = 0

    try:
        with storage_path.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > settings.max_audio_file_size_bytes:
                    raise AudioFileTooLargeError(settings.max_audio_file_size_mb)
                hasher.update(chunk)
                output.write(chunk)
    except Exception:
        storage_path.unlink(missing_ok=True)
        raise

    if total_size == 0:
        storage_path.unlink(missing_ok=True)
        raise EmptyAudioFileError()

    return StoredAudio(
        original_file_name=original_file_name,
        stored_file_name=stored_file_name,
        storage_path=str(storage_path),
        file_hash=hasher.hexdigest(),
        file_size_bytes=total_size,
        extension=extension,
    )

