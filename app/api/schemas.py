from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

InterpretationStyle = Literal["conservative", "balanced", "interpretative"]
FeedbackRating = Literal["positive", "neutral", "negative"]


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    python_version: str
    transcription_engine: str
    whisper_model_size: str
    emotion_provider: str
    cohere_enabled: bool
    database_url: str
    storage_dirs: dict[str, str]


class SystemStatusResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    python_version: str
    transcription_engine: str
    whisper_model_size: str
    emotion_provider: str
    cohere_enabled: bool
    cohere_configured: bool
    database_url: str
    storage_dirs: dict[str, str]
    ffmpeg_available: bool
    database_exists: bool
    analyses_count: int
    learning_examples_count: int


class AnalysisMetadata(BaseModel):
    file_name: str
    file_hash: str
    language: str
    duration_seconds: float
    audio_duration_seconds: float
    processing_version: str
    external_ai_used: bool
    created_at: datetime


class ProcessingStatus(BaseModel):
    acoustic_metrics_status: Literal["real"]
    transcription_status: Literal["real", "mocked"]
    emotion_status: Literal["real", "fallback_local", "mocked"]
    emotion_analysis_source: str | None = None


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    confidence: float | None = None


class TranscriptionWord(BaseModel):
    word: str
    start: float
    end: float
    duration_ms: int
    pause_before_ms: int
    pause_after_ms: int
    confidence: float | None = None


class Transcription(BaseModel):
    text: str
    segments: list[TranscriptionSegment]
    words: list[TranscriptionWord]
    transcription_engine: str
    transcription_model: str
    detected_language: str
    word_count: int
    words_per_minute: float
    estimated_speech_rate_label: Literal["slow", "normal", "fast"]
    average_word_duration_ms: float | None = None


class AnnotatedTranscription(BaseModel):
    text: str
    annotation_style: str = "inline_brackets"
    language: str
    analysis_source: str | None = None


class EmphasisWord(BaseModel):
    word: str
    start: float
    end: float
    emphasis_score: float
    reason: str


class ProsodySummary(BaseModel):
    speech_rate_wpm: float
    pace: str
    avg_volume_db: float
    max_volume_db: float
    volume_variance: float
    pause_ratio: float
    emphasis_words: list[EmphasisWord]
    calmness_score: float
    tension_score: float


class PeakEvent(BaseModel):
    time_seconds: float
    volume_db: float
    intensity_label: str


class VolumeTimelinePoint(BaseModel):
    start_seconds: float
    end_seconds: float
    volume_db: float


class AcousticMetrics(BaseModel):
    duration_seconds: float
    sample_rate: int
    avg_volume_db: float
    peak_volume_db: float
    volume_variance: float
    dynamic_range_db: float
    silence_count: int
    total_silence_duration_seconds: float
    silence_ratio: float
    longest_silence_seconds: float
    estimated_speech_duration_seconds: float
    peak_count: int
    peak_events: list[PeakEvent]
    volume_timeline: list[VolumeTimelinePoint]
    is_mostly_silent: bool
    audio_quality_warning: str | None = None
    analysis_window_seconds: float


class EmotionSummary(BaseModel):
    primary_emotion: str
    secondary_emotions: list[str]
    implicit_emotion: str
    emotional_tone: str | None = None
    interlocutor_calmness: str
    calmness_level: str | None = None
    urgency_level: str
    intention: str
    calmness_score: float | None = None
    tension_score: float | None = None
    confidence_score: float
    interpretation_style: InterpretationStyle
    interpretation_summary: str | None = None
    analysis_source: str | None = None
    analysis_model: str | None = None
    analysis_status: str | None = None


class EmotionEvidence(BaseModel):
    type: str
    signal: str
    value: Any = None
    impact: str


class EmotionDebug(BaseModel):
    provider_requested: str = "hybrid"
    cohere_enabled: bool = False
    cohere_attempted: bool = False
    cohere_success: bool = False
    fallback_used: bool = True
    fallback_reason: str | None = None
    local_fallback_result: dict = Field(default_factory=dict)
    cohere_result_raw_excerpt: str | None = None
    learning_examples_count: int = 0
    learning_examples_requested: bool = False
    learning_examples_found: int = 0
    learning_examples_used_count: int = 0
    learning_min_similarity: float | None = None
    top_learning_examples: list[dict] = Field(default_factory=list)
    learning_influence_applied: bool = False
    learning_influence_summary: str | None = None
    whether_learning_changed_result: bool = False
    learning_adjustments: list[str] = Field(default_factory=list)
    heuristic_weights_snapshot: dict = Field(default_factory=dict)
    heuristic_scores: dict = Field(default_factory=dict)
    final_decision_factors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EmotionComparison(BaseModel):
    local_before_learning: str | None = None
    local_after_learning: str | None = None
    local_primary_emotion: str | None = None
    cohere_primary_emotion: str | None = None
    cohere_result: str | None = None
    agreement_level: Literal["full", "partial", "different", "local_only", "unavailable"] = "unavailable"
    learning_changed_local_result: bool = False
    differences: list[str] = Field(default_factory=list)


class LearningExampleReference(BaseModel):
    id: int
    source_analysis_id: str | None = None
    text_excerpt: str
    corrected_prediction: dict
    similarity_score: float
    matched_terms: list[str] = Field(default_factory=list)
    metric_similarity: float = 0.0
    text_similarity: float = 0.0
    recency_score: float = 0.0
    correction_summary: str | None = None
    reason_used: str | None = None
    approved_for_reuse: bool = True
    corrected_primary_emotion: str | None = None
    corrected_tone: str | None = None


class FeedbackInfo(BaseModel):
    feedback_url: str
    message: str


class AudioAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    metadata: AnalysisMetadata
    status: ProcessingStatus
    acoustic_metrics: AcousticMetrics
    transcription: Transcription
    annotated_transcription: AnnotatedTranscription
    prosody_summary: ProsodySummary
    emotion_summary: EmotionSummary
    important_observations: list[str]
    recommended_context_for_ai_agent: str
    emotion_evidence: list[EmotionEvidence] = Field(default_factory=list)
    emotion_debug: EmotionDebug = Field(default_factory=EmotionDebug)
    emotion_comparison: EmotionComparison = Field(default_factory=EmotionComparison)
    learning_examples_used: list[LearningExampleReference] = Field(default_factory=list)
    learning_influence_summary: str | None = None
    whether_learning_changed_result: bool = False
    learning_adjustments: list[str] = Field(default_factory=list)
    quality_warnings: list[str]
    feedback: FeedbackInfo


class AnalysisListResponse(BaseModel):
    analyses: list[AudioAnalysisResponse]
    limit: int
    offset: int
    count: int


class EmotionFeedbackRequest(BaseModel):
    rating: FeedbackRating
    is_correct: bool
    corrected_primary_emotion: str | None = None
    corrected_secondary_emotions: list[str] | None = None
    corrected_intention: str | None = None
    corrected_tone: str | None = None
    correction_reason: str | None = Field(default=None, max_length=2000)
    approved_for_learning: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


class FeedbackResponse(BaseModel):
    id: int
    analysis_id: str
    rating: FeedbackRating
    is_correct: bool
    learning_example_created: bool
    message: str
    created_at: datetime


class LearningExampleResponse(BaseModel):
    id: int
    source_analysis_id: str
    text_excerpt: str
    original_prediction: dict
    corrected_prediction: dict
    original_primary_emotion: str | None = None
    original_secondary_emotions: list[str] = Field(default_factory=list)
    original_tone: str | None = None
    corrected_primary_emotion: str | None = None
    corrected_tone: str | None = None
    correction_reason: str | None = None
    metrics_snapshot: dict = Field(default_factory=dict)
    acoustic_metrics_snapshot: dict = Field(default_factory=dict)
    speech_rate_snapshot: dict = Field(default_factory=dict)
    transcription_excerpt: str | None = None
    emotion_status: str | None = None
    emotion_analysis_source: str | None = None
    user_notes: str | None
    approved_for_reuse: bool
    created_at: datetime
    updated_at: datetime | None = None


class LearningExamplesListResponse(BaseModel):
    examples: list[LearningExampleResponse]
    count: int


class LearningExampleUpdateRequest(BaseModel):
    approved_for_reuse: bool | None = None
    user_notes: str | None = Field(default=None, max_length=2000)
    corrected_primary_emotion: str | None = Field(default=None, max_length=200)
    corrected_tone: str | None = Field(default=None, max_length=300)
    correction_reason: str | None = Field(default=None, max_length=2000)


class AnalysisDebugResponse(BaseModel):
    analysis_id: str
    status: ProcessingStatus
    emotion_debug: EmotionDebug
    emotion_comparison: EmotionComparison


class LearningContextResponse(BaseModel):
    analysis_id: str
    examples: list[LearningExampleReference]
    count: int
