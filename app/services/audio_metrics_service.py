from pathlib import Path
import math
import wave

import numpy as np

from app.api.schemas import AcousticMetrics, PeakEvent, VolumeTimelinePoint
from app.core.config import Settings, get_settings
from app.core.errors import AudioDurationTooLongError, EmptyAudioFileError, InvalidAudioFileError
from app.services.audio_preprocessor import ProcessedAudio

EPSILON = 1e-10
DB_FLOOR = -120.0
DEFAULT_WINDOW_SECONDS = 0.5
SILENCE_THRESHOLD_DB = -45.0
MIN_SILENCE_SECONDS = 0.3
SILENCE_FRAME_SECONDS = 0.05


def _amplitude_to_db(amplitude: float) -> float:
    if amplitude <= EPSILON:
        return DB_FLOOR
    return max(DB_FLOOR, 20.0 * math.log10(amplitude))


def _round(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _read_wav_mono(path: str) -> tuple[np.ndarray, int]:
    try:
        with wave.open(path, "rb") as audio:
            sample_rate = audio.getframerate()
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            frame_count = audio.getnframes()
            raw = audio.readframes(frame_count)
    except (wave.Error, EOFError, OSError) as exc:
        raise InvalidAudioFileError() from exc

    if frame_count <= 0 or not raw:
        raise EmptyAudioFileError()

    if sample_width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise InvalidAudioFileError()

    if channels > 1:
        try:
            samples = samples.reshape(-1, channels).mean(axis=1)
        except ValueError as exc:
            raise InvalidAudioFileError() from exc

    if samples.size == 0:
        raise EmptyAudioFileError()

    return np.clip(samples, -1.0, 1.0), sample_rate


def _build_timeline(
    samples: np.ndarray,
    sample_rate: int,
    window_seconds: float,
) -> list[VolumeTimelinePoint]:
    window_size = max(1, int(sample_rate * window_seconds))
    timeline: list[VolumeTimelinePoint] = []

    for start in range(0, samples.size, window_size):
        end = min(start + window_size, samples.size)
        window = samples[start:end]
        rms = float(np.sqrt(np.mean(np.square(window)))) if window.size else 0.0
        timeline.append(
            VolumeTimelinePoint(
                start_seconds=_round(start / sample_rate),
                end_seconds=_round(end / sample_rate),
                volume_db=_round(_amplitude_to_db(rms), 2),
            )
        )

    return timeline


def _silence_metrics(
    samples: np.ndarray,
    sample_rate: int,
    total_duration: float,
) -> tuple[int, float, float]:
    frame_size = max(1, int(sample_rate * SILENCE_FRAME_SECONDS))
    silence_count = 0
    total_silence = 0.0
    longest_silence = 0.0
    current_silence = 0.0

    for start in range(0, samples.size, frame_size):
        end = min(start + frame_size, samples.size)
        frame = samples[start:end]
        frame_duration = (end - start) / sample_rate
        rms = float(np.sqrt(np.mean(np.square(frame)))) if frame.size else 0.0
        if _amplitude_to_db(rms) <= SILENCE_THRESHOLD_DB:
            current_silence += frame_duration
            continue

        if current_silence >= MIN_SILENCE_SECONDS:
            silence_count += 1
            total_silence += current_silence
            longest_silence = max(longest_silence, current_silence)
        current_silence = 0.0

    if current_silence >= MIN_SILENCE_SECONDS:
        silence_count += 1
        total_silence += current_silence
        longest_silence = max(longest_silence, current_silence)

    return silence_count, min(total_silence, total_duration), longest_silence


def _intensity_label(volume_db: float) -> str:
    if volume_db >= -12.0:
        return "high"
    if volume_db >= -24.0:
        return "medium"
    return "low"


def _peak_events(
    timeline: list[VolumeTimelinePoint],
    avg_volume_db: float,
) -> list[PeakEvent]:
    if not timeline:
        return []

    volumes = np.array([point.volume_db for point in timeline], dtype=np.float32)
    dynamic_range = float(np.percentile(volumes, 95) - np.percentile(volumes, 10))
    threshold = max(avg_volume_db + 6.0, -18.0)
    if dynamic_range >= 6.0:
        threshold = min(threshold, float(np.percentile(volumes, 90)))

    events: list[PeakEvent] = []
    current_group: list[VolumeTimelinePoint] = []

    def flush_group() -> None:
        if not current_group:
            return
        loudest = max(current_group, key=lambda item: item.volume_db)
        events.append(
            PeakEvent(
                time_seconds=_round((loudest.start_seconds + loudest.end_seconds) / 2),
                volume_db=_round(loudest.volume_db, 2),
                intensity_label=_intensity_label(loudest.volume_db),
            )
        )
        current_group.clear()

    for point in timeline:
        is_peak = point.volume_db > SILENCE_THRESHOLD_DB and point.volume_db >= threshold
        if is_peak:
            current_group.append(point)
        else:
            flush_group()

    flush_group()

    return sorted(events, key=lambda item: item.volume_db, reverse=True)[:10]


def _quality_warning(
    *,
    avg_volume_db: float,
    peak_volume_db: float,
    dynamic_range_db: float,
    silence_ratio: float,
) -> str | None:
    if silence_ratio >= 0.85:
        return "Áudio majoritariamente silencioso."
    if avg_volume_db <= -55.0:
        return "Áudio muito baixo."
    if peak_volume_db >= -1.0:
        return "Possível clipping ou pico muito próximo de 0 dB."
    if dynamic_range_db >= 35.0:
        return "Volume muito instável ao longo do áudio."
    return None


def calculate_acoustic_metrics(
    processed_audio: ProcessedAudio,
    settings: Settings | None = None,
    *,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
) -> AcousticMetrics:
    settings = settings or get_settings()
    samples, sample_rate = _read_wav_mono(processed_audio.processed_path)

    duration_seconds = samples.size / sample_rate
    if duration_seconds <= 0:
        raise EmptyAudioFileError()
    if duration_seconds > settings.max_audio_duration_seconds:
        Path(processed_audio.processed_path).unlink(missing_ok=True)
        raise AudioDurationTooLongError(settings.max_audio_duration_seconds)

    rms = float(np.sqrt(np.mean(np.square(samples))))
    peak = float(np.max(np.abs(samples)))
    avg_volume_db = _amplitude_to_db(rms)
    peak_volume_db = _amplitude_to_db(peak)

    timeline = _build_timeline(samples, sample_rate, window_seconds)
    timeline_volumes = np.array([point.volume_db for point in timeline], dtype=np.float32)
    volume_variance = float(np.var(timeline_volumes)) if timeline_volumes.size else 0.0
    dynamic_range_db = (
        float(np.percentile(timeline_volumes, 95) - np.percentile(timeline_volumes, 10))
        if timeline_volumes.size
        else 0.0
    )

    silence_count, total_silence, longest_silence = _silence_metrics(
        samples,
        sample_rate,
        duration_seconds,
    )
    silence_ratio = total_silence / duration_seconds if duration_seconds else 0.0
    estimated_speech_duration = max(0.0, duration_seconds - total_silence)
    peak_events = _peak_events(timeline, avg_volume_db)

    return AcousticMetrics(
        duration_seconds=_round(duration_seconds),
        sample_rate=sample_rate,
        avg_volume_db=_round(avg_volume_db, 2),
        peak_volume_db=_round(peak_volume_db, 2),
        volume_variance=_round(volume_variance, 3),
        dynamic_range_db=_round(dynamic_range_db, 2),
        silence_count=silence_count,
        total_silence_duration_seconds=_round(total_silence),
        silence_ratio=_round(silence_ratio, 3),
        longest_silence_seconds=_round(longest_silence),
        estimated_speech_duration_seconds=_round(estimated_speech_duration),
        peak_count=len(peak_events),
        peak_events=peak_events,
        volume_timeline=timeline,
        is_mostly_silent=silence_ratio >= 0.85 or avg_volume_db <= -55.0,
        audio_quality_warning=_quality_warning(
            avg_volume_db=avg_volume_db,
            peak_volume_db=peak_volume_db,
            dynamic_range_db=dynamic_range_db,
            silence_ratio=silence_ratio,
        ),
        analysis_window_seconds=window_seconds,
    )
