from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv(override=False)


def _env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value is not None and value != "":
            return value
    return default


def _bool(value: str, *, default: bool = False) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int(value: str, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: str, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _extensions(value: str) -> tuple[str, ...]:
    raw_extensions = value or "mp3,wav,m4a,webm,ogg"
    extensions: list[str] = []
    required_extensions = ("mp3", "wav", "m4a", "webm", "ogg")
    for item in [*raw_extensions.split(","), *required_extensions]:
        normalized = item.strip().lower()
        if not normalized:
            continue
        if not normalized.startswith("."):
            normalized = f".{normalized}"
        extensions.append(normalized)
    return tuple(dict.fromkeys(extensions))


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str
    app_env: str
    app_debug: bool
    app_version: str

    database_url: str

    cohere_api_key: str
    cohere_model: str
    cohere_chat_model: str
    cohere_enabled: bool
    use_cohere: bool

    emotion_analysis_provider: str
    emotion_use_learning_examples: bool
    emotion_max_learning_examples: int
    emotion_confidence_threshold: float
    emotion_learning_min_similarity: float
    emotion_learning_example_weight: float
    emotion_text_urgency_weight: float
    emotion_text_negative_weight: float
    emotion_high_volume_weight: float
    emotion_low_volume_weight: float
    emotion_silence_ratio_weight: float
    emotion_speech_rate_weight: float
    emotion_peak_volume_weight: float
    emotion_cohere_weight: float
    emotion_fallback_weight: float
    emotion_high_silence_ratio_threshold: float
    emotion_low_wpm_threshold: float
    emotion_high_wpm_threshold: float
    emotion_high_peak_threshold: float
    emotion_low_volume_threshold: float

    max_audio_duration_seconds: int
    max_audio_file_size_mb: int
    default_language: str
    allowed_audio_extensions: tuple[str, ...]

    transcription_provider: str
    local_transcription_engine: str
    whisper_model_size: str
    whisper_device: str
    whisper_compute_type: str

    storage_dir: str
    audio_storage_dir: str
    processed_audio_dir: str
    exports_dir: str = "exports"

    @property
    def max_audio_file_size_bytes(self) -> int:
        return self.max_audio_file_size_mb * 1024 * 1024

    @property
    def external_ai_available(self) -> bool:
        return self.cohere_enabled and self.use_cohere and bool(self.cohere_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    storage_dir = _env("STORAGE_DIR", default="storage")

    return Settings(
        app_name=_env("APP_NAME", default="Audio Emotion API"),
        app_env=_env("APP_ENV", default="local"),
        app_debug=_bool(_env("APP_DEBUG", "DEBUG", default="true"), default=True),
        app_version=_env("APP_VERSION", default="0.5.0"),
        database_url=_env("DATABASE_URL", default="sqlite:///./audio_emotion.db"),
        cohere_api_key=_env("COHERE_API_KEY", default=""),
        cohere_model=_env("COHERE_MODEL", "COHERE_CHAT_MODEL", default="command-a-03-2025"),
        cohere_chat_model=_env("COHERE_CHAT_MODEL", "COHERE_MODEL", default="command-a-03-2025"),
        cohere_enabled=_bool(_env("COHERE_ENABLED", "USE_COHERE", default="true"), default=True),
        use_cohere=_bool(_env("USE_COHERE", "COHERE_ENABLED", default="true"), default=True),
        emotion_analysis_provider=_env("EMOTION_ANALYSIS_PROVIDER", default="hybrid"),
        emotion_use_learning_examples=_bool(
            _env("EMOTION_USE_LEARNING_EXAMPLES", default="true"),
            default=True,
        ),
        emotion_max_learning_examples=_int(
            _env("EMOTION_MAX_LEARNING_EXAMPLES", default="3"),
            default=3,
        ),
        emotion_confidence_threshold=_float(
            _env("EMOTION_CONFIDENCE_THRESHOLD", default="0.50"),
            default=0.50,
        ),
        emotion_learning_min_similarity=_float(
            _env("EMOTION_LEARNING_MIN_SIMILARITY", default="0.20"),
            default=0.20,
        ),
        emotion_learning_example_weight=_float(
            _env("EMOTION_LEARNING_EXAMPLE_WEIGHT", default="0.25"),
            default=0.25,
        ),
        emotion_text_urgency_weight=_float(
            _env("EMOTION_TEXT_URGENCY_WEIGHT", default="0.14"),
            default=0.14,
        ),
        emotion_text_negative_weight=_float(
            _env("EMOTION_TEXT_NEGATIVE_WEIGHT", default="0.12"),
            default=0.12,
        ),
        emotion_high_volume_weight=_float(
            _env("EMOTION_HIGH_VOLUME_WEIGHT", default="0.12"),
            default=0.12,
        ),
        emotion_low_volume_weight=_float(
            _env("EMOTION_LOW_VOLUME_WEIGHT", default="0.10"),
            default=0.10,
        ),
        emotion_silence_ratio_weight=_float(
            _env("EMOTION_SILENCE_RATIO_WEIGHT", default="0.15"),
            default=0.15,
        ),
        emotion_speech_rate_weight=_float(
            _env("EMOTION_SPEECH_RATE_WEIGHT", default="0.10"),
            default=0.10,
        ),
        emotion_peak_volume_weight=_float(
            _env("EMOTION_PEAK_VOLUME_WEIGHT", default="0.12"),
            default=0.12,
        ),
        emotion_cohere_weight=_float(
            _env("EMOTION_COHERE_WEIGHT", default="0.65"),
            default=0.65,
        ),
        emotion_fallback_weight=_float(
            _env("EMOTION_FALLBACK_WEIGHT", default="0.35"),
            default=0.35,
        ),
        emotion_high_silence_ratio_threshold=_float(
            _env("EMOTION_HIGH_SILENCE_RATIO_THRESHOLD", default="0.35"),
            default=0.35,
        ),
        emotion_low_wpm_threshold=_float(
            _env("EMOTION_LOW_WPM_THRESHOLD", default="85"),
            default=85.0,
        ),
        emotion_high_wpm_threshold=_float(
            _env("EMOTION_HIGH_WPM_THRESHOLD", default="150"),
            default=150.0,
        ),
        emotion_high_peak_threshold=_float(
            _env("EMOTION_HIGH_PEAK_THRESHOLD", default="-8.0"),
            default=-8.0,
        ),
        emotion_low_volume_threshold=_float(
            _env("EMOTION_LOW_VOLUME_THRESHOLD", default="-30.0"),
            default=-30.0,
        ),
        max_audio_duration_seconds=_int(
            _env("MAX_AUDIO_DURATION_SECONDS", default="600"),
            default=600,
        ),
        max_audio_file_size_mb=_int(
            _env("MAX_AUDIO_FILE_SIZE_MB", "MAX_AUDIO_SIZE_MB", default="100"),
            default=100,
        ),
        default_language=_env("DEFAULT_LANGUAGE", default="pt-BR"),
        allowed_audio_extensions=_extensions(
            _env("ALLOWED_AUDIO_EXTENSIONS", default="mp3,wav,m4a,webm,ogg")
        ),
        transcription_provider=_env("TRANSCRIPTION_PROVIDER", default="local"),
        local_transcription_engine=_env("LOCAL_TRANSCRIPTION_ENGINE", default="faster-whisper"),
        whisper_model_size=_env("WHISPER_MODEL_SIZE", default="tiny"),
        whisper_device=_env("WHISPER_DEVICE", default="cpu"),
        whisper_compute_type=_env("WHISPER_COMPUTE_TYPE", default="int8"),
        storage_dir=storage_dir,
        audio_storage_dir=_env("AUDIO_STORAGE_DIR", "TEMP_AUDIO_DIR", default=f"{storage_dir}/audio"),
        processed_audio_dir=_env(
            "PROCESSED_AUDIO_DIR",
            "PROCESSED_AUDIO_STORAGE_DIR",
            default=f"{storage_dir}/processed",
        ),
        exports_dir=_env("EXPORTS_DIR", default="exports"),
    )


def ensure_storage_directories() -> None:
    settings = get_settings()
    for directory in (
        settings.storage_dir,
        settings.audio_storage_dir,
        settings.processed_audio_dir,
        settings.exports_dir,
    ):
        Path(directory).mkdir(parents=True, exist_ok=True)
