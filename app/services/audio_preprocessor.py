from pathlib import Path
import shutil
import subprocess

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.errors import AudioConversionError, FFmpegNotFoundError
from app.services.audio_loader import StoredAudio


class ProcessedAudio(BaseModel):
    original_path: str
    processed_path: str
    sample_rate: int = 16000
    channels: int = 1
    codec: str = "pcm_s16le"


def standardize_audio(
    stored_audio: StoredAudio,
    settings: Settings | None = None,
) -> ProcessedAudio:
    settings = settings or get_settings()
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        raise FFmpegNotFoundError()

    processed_dir = Path(settings.processed_audio_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(stored_audio.storage_path)
    output_name = f"{input_path.stem}_16khz_mono.wav"
    output_path = processed_dir / output_name

    command = [
        ffmpeg_path,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-acodec",
        "pcm_s16le",
        str(output_path),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            encoding="utf-8",
            errors="replace",
            text=True,
            timeout=max(60, settings.max_audio_duration_seconds * 2),
        )
    except subprocess.TimeoutExpired as exc:
        output_path.unlink(missing_ok=True)
        raise AudioConversionError() from exc
    except OSError as exc:
        output_path.unlink(missing_ok=True)
        raise AudioConversionError() from exc

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise AudioConversionError()

    return ProcessedAudio(
        original_path=str(input_path),
        processed_path=str(output_path),
    )
