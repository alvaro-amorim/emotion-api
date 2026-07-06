from functools import lru_cache
import math
import re
from typing import Any

from app.api.schemas import AcousticMetrics, Transcription, TranscriptionSegment, TranscriptionWord
from app.core.config import Settings, get_settings
from app.core.errors import TranscriptionError
from app.services.audio_preprocessor import ProcessedAudio

WORD_PATTERN = re.compile(r"[\wÀ-ÿ']+", re.UNICODE)


def _language_for_whisper(language: str) -> str:
    normalized = language.strip().lower()
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
        raw_segments, info = model.transcribe(
            processed_audio.processed_path,
            language=_language_for_whisper(language),
            word_timestamps=True,
            beam_size=1,
        )
        segments = list(raw_segments)
    except Exception as exc:
        raise TranscriptionError() from exc

    detected_language = getattr(info, "language", None) or _language_for_whisper(language)
    return build_transcription_from_segments(
        segments,
        audio_duration_seconds=acoustic_metrics.duration_seconds,
        transcription_engine=settings.local_transcription_engine,
        transcription_model=settings.whisper_model_size,
        detected_language=detected_language,
    )
