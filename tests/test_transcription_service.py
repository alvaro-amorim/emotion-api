from types import SimpleNamespace

from app.api.schemas import AcousticMetrics
from app.services.audio_preprocessor import ProcessedAudio
from app.services.transcription_service import (
    build_transcription_from_segments,
    build_transcription_quality,
    normalize_whisper_language,
)


def test_build_transcription_from_segments_normalizes_words_and_speech_rate():
    segments = [
        SimpleNamespace(
            id=0,
            start=0.0,
            end=1.2,
            text="Olá mundo",
            avg_logprob=-0.2,
            words=[
                SimpleNamespace(word="Olá", start=0.0, end=0.35, probability=0.92),
                SimpleNamespace(word="mundo", start=0.55, end=1.0, probability=0.88),
            ],
        )
    ]

    transcription = build_transcription_from_segments(
        segments,
        audio_duration_seconds=2.0,
        transcription_engine="faster-whisper",
        transcription_model="tiny",
        detected_language="pt",
    )

    assert transcription.text == "Olá mundo"
    assert transcription.segments[0].confidence is not None
    assert transcription.words[0].word == "Olá"
    assert transcription.words[0].pause_after_ms == 200
    assert transcription.words[1].pause_before_ms == 200
    assert transcription.word_count == 2
    assert transcription.words_per_minute == 60.0
    assert transcription.estimated_speech_rate_label == "slow"
    assert transcription.average_word_duration_ms == 400.0


def test_normalize_whisper_language_maps_pt_br_to_pt():
    assert normalize_whisper_language("pt-BR") == "pt"
    assert normalize_whisper_language("pt_BR") == "pt"
    assert normalize_whisper_language("en-US") == "en"
    assert normalize_whisper_language("") == "pt"


def test_transcription_quality_warns_for_silence_and_clipping():
    transcription = build_transcription_from_segments(
        [
            SimpleNamespace(
                id=0,
                start=0.0,
                end=0.5,
                text="teste curto",
                avg_logprob=-1.2,
                words=[],
            )
        ],
        audio_duration_seconds=0.8,
        transcription_engine="faster-whisper",
        transcription_model="tiny",
        detected_language="pt",
    )
    metrics = AcousticMetrics(
        duration_seconds=0.8,
        sample_rate=16000,
        avg_volume_db=-18.0,
        peak_volume_db=-0.2,
        volume_variance=1.0,
        dynamic_range_db=5.0,
        silence_count=1,
        total_silence_duration_seconds=0.5,
        silence_ratio=0.625,
        longest_silence_seconds=0.5,
        estimated_speech_duration_seconds=0.3,
        peak_count=1,
        peak_events=[],
        volume_timeline=[],
        is_mostly_silent=False,
        audio_quality_warning="Possível clipping ou pico muito próximo de 0 dB.",
        analysis_window_seconds=0.5,
    )
    processed_audio = ProcessedAudio(
        original_path="storage/audio/test.wav",
        processed_path="storage/processed/test_transcription.wav",
        optimized_for_transcription=True,
        transcription_source_path="storage/processed/test.wav",
    )

    quality = build_transcription_quality(
        transcription=transcription,
        processed_audio=processed_audio,
        acoustic_metrics=metrics,
        language_used="pt",
    )

    assert quality.language_used == "pt"
    assert quality.used_optimized_audio is True
    assert quality.low_confidence is True
    assert any("Silêncio" in warning for warning in quality.warnings)
    assert any("clipping" in warning.lower() for warning in quality.warnings)


def test_whisper_parameters_are_read_from_env(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("WHISPER_BEAM_SIZE", "7")
    monkeypatch.setenv("WHISPER_BEST_OF", "3")
    monkeypatch.setenv("WHISPER_TEMPERATURE", "0.2")
    monkeypatch.setenv("WHISPER_VAD_FILTER", "false")
    monkeypatch.setenv("WHISPER_CONDITION_ON_PREVIOUS_TEXT", "true")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.whisper_beam_size == 7
    assert settings.whisper_best_of == 3
    assert settings.whisper_temperature == 0.2
    assert settings.whisper_vad_filter is False
    assert settings.whisper_condition_on_previous_text is True

    get_settings.cache_clear()
