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
    optimized_for_transcription: bool = False
    transcription_source_path: str | None = None
    transcription_fallback_reason: str | None = None


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


def optimize_audio_for_transcription(
    processed_audio: ProcessedAudio,
    settings: Settings | None = None,
) -> ProcessedAudio:
    """Generate a lightly filtered WAV for Whisper without changing acoustic metrics input."""
    settings = settings or get_settings()
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return processed_audio.model_copy(
            update={
                "optimized_for_transcription": False,
                "transcription_source_path": processed_audio.processed_path,
                "transcription_fallback_reason": "ffmpeg_not_found",
            }
        )

    processed_dir = Path(settings.processed_audio_dir)
    processed_dir.mkdir(parents=True, exist_ok=True)

    input_path = Path(processed_audio.processed_path)
    output_path = processed_dir / f"{input_path.stem}_transcription.wav"

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
        "-af",
        "highpass=f=80,lowpass=f=8000,dynaudnorm=f=150:g=5:p=0.8:m=5",
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
    except (subprocess.TimeoutExpired, OSError):
        output_path.unlink(missing_ok=True)
        return processed_audio.model_copy(
            update={
                "optimized_for_transcription": False,
                "transcription_source_path": processed_audio.processed_path,
                "transcription_fallback_reason": "optimized_conversion_failed",
            }
        )

    if result.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        return processed_audio.model_copy(
            update={
                "optimized_for_transcription": False,
                "transcription_source_path": processed_audio.processed_path,
                "transcription_fallback_reason": "optimized_conversion_failed",
            }
        )

    return ProcessedAudio(
        original_path=processed_audio.original_path,
        processed_path=str(output_path),
        sample_rate=processed_audio.sample_rate,
        channels=processed_audio.channels,
        codec=processed_audio.codec,
        optimized_for_transcription=True,
        transcription_source_path=processed_audio.processed_path,
    )
