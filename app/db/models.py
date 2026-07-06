from datetime import datetime, timezone
from uuid import uuid4

from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioAnalysis(SQLModel, table=True):
    __tablename__ = "audio_analysis"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    file_name: str
    file_hash: str = Field(index=True)
    duration_seconds: float
    language: str = Field(default="pt-BR", index=True)
    transcription_text: str
    transcription_segments_json: str = "[]"
    transcription_words_json: str = "[]"
    transcription_engine: str | None = None
    transcription_model: str | None = None
    transcription_status: str = "mocked"
    detected_language: str | None = None
    word_count: int = 0
    words_per_minute: float = 0.0
    estimated_speech_rate_label: str | None = None
    average_word_duration_ms: float | None = None
    annotated_transcription: str
    final_summary_json: str
    emotion_status: str = "mocked"
    emotion_analysis_source: str | None = None
    emotion_analysis_model: str | None = None
    emotion_summary_json: str = "{}"
    primary_emotion: str | None = None
    secondary_emotions_json: str = "[]"
    confidence_score: float = 0.0
    learning_examples_used_json: str = "[]"
    warnings_json: str = "[]"
    emotion_debug_json: str = "{}"
    emotion_comparison_json: str = "{}"
    learning_influence_summary: str | None = None
    learning_adjustments_json: str = "[]"
    recommended_context_for_ai_agent: str
    external_ai_used: bool = False
    processing_version: str = "0.1.0"
    created_at: datetime = Field(default_factory=utc_now, index=True)


class AudioMetrics(SQLModel, table=True):
    __tablename__ = "audio_metrics"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: str = Field(foreign_key="audio_analysis.id", index=True)
    duration_seconds: float = 0.0
    sample_rate: int = 0
    avg_volume_db: float = 0.0
    max_volume_db: float = 0.0
    peak_volume_db: float = 0.0
    volume_variance: float = 0.0
    dynamic_range_db: float = 0.0
    silence_count: int = 0
    total_silence_duration_seconds: float = 0.0
    silence_ratio: float = 0.0
    longest_silence_seconds: float = 0.0
    estimated_speech_duration_seconds: float = 0.0
    peak_count: int = 0
    peak_events_json: str = "[]"
    volume_timeline_json: str = "[]"
    is_mostly_silent: bool = False
    audio_quality_warning: str | None = None
    analysis_window_seconds: float = 0.5
    speech_rate_wpm: float = 0.0
    pause_ratio: float = 0.0
    calmness_score: float = 0.0
    tension_score: float = 0.0
    created_at: datetime = Field(default_factory=utc_now)


class WordMetrics(SQLModel, table=True):
    __tablename__ = "word_metrics"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: str = Field(foreign_key="audio_analysis.id", index=True)
    word: str
    start_time: float
    end_time: float
    duration_ms: int
    pause_before_ms: int
    pause_after_ms: int
    volume_at_word: float
    emphasis_score: float
    confidence: float
    comment: str | None = None


class EmotionFeedback(SQLModel, table=True):
    __tablename__ = "emotion_feedback"

    id: int | None = Field(default=None, primary_key=True)
    analysis_id: str = Field(foreign_key="audio_analysis.id", index=True)
    rating: str
    is_correct: bool
    corrected_primary_emotion: str | None = None
    corrected_secondary_emotions: str | None = None
    corrected_intention: str | None = None
    corrected_tone: str | None = None
    correction_reason: str | None = None
    approved_for_learning: bool | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=utc_now, index=True)


class LearningExample(SQLModel, table=True):
    __tablename__ = "learning_examples"

    id: int | None = Field(default=None, primary_key=True)
    source_analysis_id: str = Field(foreign_key="audio_analysis.id", index=True)
    text_excerpt: str
    original_prediction: str
    corrected_prediction: str
    metrics_snapshot_json: str = "{}"
    acoustic_metrics_snapshot_json: str = "{}"
    speech_rate_snapshot_json: str = "{}"
    transcription_excerpt: str | None = None
    emotion_status: str | None = None
    emotion_analysis_source: str | None = None
    original_primary_emotion: str | None = None
    original_secondary_emotions_json: str = "[]"
    original_tone: str | None = None
    corrected_primary_emotion: str | None = None
    corrected_tone: str | None = None
    correction_reason: str | None = None
    user_notes: str | None = None
    approved_for_reuse: bool = False
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime | None = None
