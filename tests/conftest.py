from pathlib import Path
import io
import math
import wave

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    storage_dir = tmp_path / "storage"
    db_path = tmp_path / "audio_emotion_test.db"

    monkeypatch.setenv("APP_NAME", "Audio Emotion API")
    monkeypatch.setenv("APP_VERSION", "0.5.0")
    monkeypatch.setenv("APP_DEBUG", "false")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("REQUIRE_API_KEY", "false")
    monkeypatch.setenv("LOCAL_API_KEY", "test-local-key")
    monkeypatch.setenv("API_KEY_HEADER_NAME", "X-API-Key")
    monkeypatch.setenv("ALLOWED_CLIENT_ORIGINS", "http://127.0.0.1:8020,http://localhost:8020")
    monkeypatch.setenv("STORAGE_DIR", str(storage_dir))
    monkeypatch.setenv("AUDIO_STORAGE_DIR", str(storage_dir / "audio"))
    monkeypatch.setenv("PROCESSED_AUDIO_DIR", str(storage_dir / "processed"))
    monkeypatch.setenv("MAX_AUDIO_FILE_SIZE_MB", "1")
    monkeypatch.setenv("MAX_AUDIO_DURATION_SECONDS", "600")
    monkeypatch.setenv("DEFAULT_LANGUAGE", "pt-BR")
    monkeypatch.setenv("ALLOWED_AUDIO_EXTENSIONS", "mp3,wav,m4a,webm,ogg")
    monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "local")
    monkeypatch.setenv("LOCAL_TRANSCRIPTION_ENGINE", "faster-whisper")
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "tiny")
    monkeypatch.setenv("WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "int8")
    monkeypatch.setenv("WHISPER_BEAM_SIZE", "5")
    monkeypatch.setenv("WHISPER_BEST_OF", "5")
    monkeypatch.setenv("WHISPER_TEMPERATURE", "0")
    monkeypatch.setenv("WHISPER_VAD_FILTER", "true")
    monkeypatch.setenv("WHISPER_CONDITION_ON_PREVIOUS_TEXT", "false")
    monkeypatch.setenv("COHERE_API_KEY", "")
    monkeypatch.setenv("USE_COHERE", "false")
    monkeypatch.setenv("COHERE_ENABLED", "false")
    monkeypatch.setenv("COHERE_CHAT_MODEL", "command-a-03-2025")
    monkeypatch.setenv("EMOTION_ANALYSIS_PROVIDER", "hybrid")
    monkeypatch.setenv("EMOTION_USE_LEARNING_EXAMPLES", "true")
    monkeypatch.setenv("EMOTION_MAX_LEARNING_EXAMPLES", "3")
    monkeypatch.setenv("EMOTION_CONFIDENCE_THRESHOLD", "0.50")
    monkeypatch.setenv("EMOTION_LEARNING_MIN_SIMILARITY", "0.20")
    monkeypatch.setenv("EMOTION_LEARNING_EXAMPLE_WEIGHT", "0.25")

    from app.api import routes_audio
    from app.api.schemas import Transcription, TranscriptionSegment, TranscriptionWord
    from app.core.config import get_settings
    from app.db.session import reset_engine_for_tests
    from app.main import app

    def fake_transcribe_audio(processed_audio, acoustic_metrics, language, settings):
        return Transcription(
            text="Eu preciso resolver este problema agora, mas estou falando com calma.",
            segments=[
                TranscriptionSegment(
                    id=0,
                    start=0.0,
                    end=min(2.0, acoustic_metrics.duration_seconds),
                    text="Eu preciso resolver este problema agora, mas estou falando com calma.",
                    confidence=0.91,
                )
            ],
            words=[
                TranscriptionWord(
                    word="Eu",
                    start=0.0,
                    end=0.3,
                    duration_ms=300,
                    pause_before_ms=0,
                    pause_after_ms=40,
                    confidence=0.93,
                ),
                TranscriptionWord(
                    word="problema",
                    start=0.9,
                    end=1.25,
                    duration_ms=350,
                    pause_before_ms=80,
                    pause_after_ms=0,
                    confidence=0.9,
                ),
            ],
            transcription_engine="faster-whisper",
            transcription_model="tiny",
            detected_language="pt",
            word_count=8,
            words_per_minute=round(8 / max(acoustic_metrics.duration_seconds, 0.001) * 60, 2),
            estimated_speech_rate_label="fast",
            average_word_duration_ms=325.0,
        )

    get_settings.cache_clear()
    reset_engine_for_tests()
    monkeypatch.setattr(routes_audio, "transcribe_audio", fake_transcribe_audio)

    with TestClient(app) as test_client:
        yield test_client

    reset_engine_for_tests()
    get_settings.cache_clear()


def create_mock_analysis(client: TestClient) -> dict:
    audio_bytes = make_wav_bytes(duration_seconds=1.0, amplitude=0.35)
    response = client.post(
        "/v1/analyze-audio",
        files={"file": ("audio_teste.wav", audio_bytes, "audio/wav")},
        data={
            "language": "pt-BR",
            "use_external_ai": "false",
            "interpretation_style": "interpretative",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_wav_bytes(
    *,
    duration_seconds: float,
    sample_rate: int = 16000,
    amplitude: float = 0.4,
    frequency: float = 440.0,
    silence_ranges: list[tuple[float, float]] | None = None,
) -> bytes:
    silence_ranges = silence_ranges or []
    total_samples = int(duration_seconds * sample_rate)
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()
        for index in range(total_samples):
            time_seconds = index / sample_rate
            is_silent = any(start <= time_seconds < end for start, end in silence_ranges)
            value = 0.0 if is_silent else amplitude * math.sin(2 * math.pi * frequency * time_seconds)
            sample = int(max(-1.0, min(1.0, value)) * 32767)
            frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

        wav.writeframes(bytes(frames))

    return buffer.getvalue()

