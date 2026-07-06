from functools import lru_cache
import inspect
import math
from pathlib import Path
import re
from typing import Any

from app.api.schemas import (
    AcousticMetrics,
    Transcription,
    TranscriptionQuality,
    TranscriptionSegment,
    TranscriptionWord,
)
from app.core.config import Settings, get_settings
from app.core.errors import TranscriptionError
from app.services.audio_preprocessor import ProcessedAudio

WORD_PATTERN = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)


def normalize_whisper_language(language: str | None) -> str:
    normalized = (language or "").strip().lower().replace("_", "-")
    if normalized.startswith("pt"):
        return "pt"
    if "-" in normalized:
        return normalized.split("-", 1)[0]
    return normalized or "pt"


def _confidence_from_logprob(value: float | None) -> float | None:
    if value is None:
        return None
    try:
        return round(max(0.0, min(1.0, math.exp(value))), 3)
    except OverflowError:
        return None


def _word_count(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def _speech_rate_label(words_per_minute: float) -> str:
    if words_per_minute < 110:
        return "slow"
    if words_per_minute > 170:
        return "fast"
    return "normal"


def _word_attr(word: Any, name: str, default: Any = None) -> Any:
    return getattr(word, name, default)


def _display_audio_path(path: str | None) -> str | None:
    if not path:
        return None
    value = Path(path)
    try:
        return value.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return value.name


def _transcribe_kwargs(model: Any, settings: Settings, language_used: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "language": language_used,
        "word_timestamps": True,
        "beam_size": settings.whisper_beam_size,
        "best_of": settings.whisper_best_of,
        "temperature": settings.whisper_temperature,
        "vad_filter": settings.whisper_vad_filter,
        "condition_on_previous_text": settings.whisper_condition_on_previous_text,
    }
    try:
        supported = set(inspect.signature(model.transcribe).parameters)
    except (TypeError, ValueError):
        return kwargs
    return {key: value for key, value in kwargs.items() if key in supported}


def _average_confidence(transcription: Transcription) -> float | None:
    segment_confidences = [
        segment.confidence for segment in transcription.segments if segment.confidence is not None
    ]
    if segment_confidences:
        return round(sum(segment_confidences) / len(segment_confidences), 3)

    word_confidences = [word.confidence for word in transcription.words if word.confidence is not None]
    if word_confidences:
        return round(sum(word_confidences) / len(word_confidences), 3)

    return None


def build_transcription_quality(
    *,
    transcription: Transcription,
    processed_audio: ProcessedAudio,
    acoustic_metrics: AcousticMetrics,
    language_used: str,
    settings: Settings | None = None,
) -> TranscriptionQuality:
    settings = settings or get_settings()
    avg_confidence = _average_confidence(transcription)
    low_confidence = avg_confidence is not None and avg_confidence < 0.55
    warnings: list[str] = []

    if low_confidence:
        warnings.append("Confiança média da transcrição baixa; revise o áudio ou use um modelo maior.")
    if acoustic_metrics.silence_ratio >= 0.45 or acoustic_metrics.is_mostly_silent:
        warnings.append("Silêncio/pausas em proporção alta podem reduzir a precisão da transcrição.")
    if acoustic_metrics.peak_volume_db >= -1.0:
        warnings.append("Pico próximo de 0 dB pode indicar clipping e prejudicar a transcrição.")
    if acoustic_metrics.duration_seconds < 1.0:
        warnings.append("Áudio muito curto; a transcrição pode ficar instável.")
    if acoustic_metrics.audio_quality_warning:
        warnings.append(acoustic_metrics.audio_quality_warning)
    if processed_audio.transcription_fallback_reason:
        warnings.append("Áudio otimizado para transcrição indisponível; WAV padrão foi usado.")

    return TranscriptionQuality(
        language_used=language_used,
        engine=settings.local_transcription_engine,
        model=settings.whisper_model_size,
        used_optimized_audio=processed_audio.optimized_for_transcription,
        audio_path=_display_audio_path(processed_audio.processed_path),
        source_audio_path=_display_audio_path(processed_audio.transcription_source_path),
        fallback_reason=processed_audio.transcription_fallback_reason,
        avg_segment_confidence=avg_confidence,
        low_confidence=low_confidence,
        warnings=list(dict.fromkeys(warnings)),
    )


def build_transcription_from_segments(
    segments: list[Any],
    *,
    audio_duration_seconds: float,
    transcription_engine: str,
    transcription_model: str,
    detected_language: str,
) -> Transcription:
    transcription_segments: list[TranscriptionSegment] = []
    transcription_words: list[TranscriptionWord] = []
    text_parts: list[str] = []

    previous_word_end: float | None = None

    for fallback_id, segment in enumerate(segments):
        segment_text = (getattr(segment, "text", "") or "").strip()
        start = float(getattr(segment, "start", 0.0) or 0.0)
        end = float(getattr(segment, "end", start) or start)
        segment_id = int(getattr(segment, "id", fallback_id) or fallback_id)
        confidence = _confidence_from_logprob(getattr(segment, "avg_logprob", None))

        if segment_text:
            text_parts.append(segment_text)

        transcription_segments.append(
            TranscriptionSegment(
                id=segment_id,
                start=round(start, 3),
                end=round(end, 3),
                text=segment_text,
                confidence=confidence,
            )
        )

        for raw_word in getattr(segment, "words", None) or []:
            word_text = str(_word_attr(raw_word, "word", "") or "").strip()
            if not word_text:
                continue

            word_start = float(_word_attr(raw_word, "start", start) or start)
            word_end = float(_word_attr(raw_word, "end", word_start) or word_start)
            duration_ms = max(0, int(round((word_end - word_start) * 1000)))
            pause_before_ms = (
                0
                if previous_word_end is None
                else max(0, int(round((word_start - previous_word_end) * 1000)))
            )
            probability = _word_attr(raw_word, "probability", None)
            confidence_value = round(float(probability), 3) if probability is not None else None

            transcription_words.append(
                TranscriptionWord(
                    word=word_text,
                    start=round(word_start, 3),
                    end=round(word_end, 3),
                    duration_ms=duration_ms,
                    pause_before_ms=pause_before_ms,
                    pause_after_ms=0,
                    confidence=confidence_value,
                )
            )
            previous_word_end = word_end

    for index, word in enumerate(transcription_words[:-1]):
        next_word = transcription_words[index + 1]
        word.pause_after_ms = max(0, int(round((next_word.start - word.end) * 1000)))

    text = " ".join(text_parts).strip()
    word_count = _word_count(text)
    words_per_minute = (
        round(word_count / max(audio_duration_seconds, 0.001) * 60, 2) if word_count else 0.0
    )
    average_word_duration_ms = (
        round(
            sum(word.duration_ms for word in transcription_words) / len(transcription_words),
            2,
        )
        if transcription_words
        else None
    )

    return Transcription(
        text=text,
        segments=transcription_segments,
        words=transcription_words,
        transcription_engine=transcription_engine,
        transcription_model=transcription_model,
        detected_language=detected_language,
        word_count=word_count,
        words_per_minute=words_per_minute,
        estimated_speech_rate_label=_speech_rate_label(words_per_minute),
        average_word_duration_ms=average_word_duration_ms,
    )


@lru_cache(maxsize=4)
def _load_faster_whisper_model(
    model_size: str,
    device: str,
    compute_type: str,
) -> Any:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError() from exc

    try:
        return WhisperModel(model_size, device=device, compute_type=compute_type)
    except Exception as exc:
        raise TranscriptionError() from exc


def transcribe_audio(
    processed_audio: ProcessedAudio,
    acoustic_metrics: AcousticMetrics,
    language: str,
    settings: Settings | None = None,
) -> Transcription:
    settings = settings or get_settings()
    if settings.transcription_provider != "local" or settings.local_transcription_engine != "faster-whisper":
        raise TranscriptionError()

    model = _load_faster_whisper_model(
        settings.whisper_model_size,
        settings.whisper_device,
        settings.whisper_compute_type,
    )

    try:
        language_used = normalize_whisper_language(language)
        raw_segments, info = model.transcribe(
            processed_audio.processed_path,
            **_transcribe_kwargs(model, settings, language_used),
        )
        segments = list(raw_segments)
    except Exception as exc:
        raise TranscriptionError() from exc

    detected_language = getattr(info, "language", None) or normalize_whisper_language(language)
    return build_transcription_from_segments(
        segments,
        audio_duration_seconds=acoustic_metrics.duration_seconds,
        transcription_engine=settings.local_transcription_engine,
        transcription_model=settings.whisper_model_size,
        detected_language=detected_language,
    )
