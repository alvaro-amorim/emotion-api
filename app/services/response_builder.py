from datetime import datetime, timezone
from uuid import uuid4

from app.api.schemas import (
    AcousticMetrics,
    AnalysisMetadata,
    AudioAnalysisResponse,
    FeedbackInfo,
    InterpretationStyle,
    LearningExampleReference,
    ProcessingStatus,
    Transcription,
)
from app.core.config import Settings, get_settings
from app.services.audio_loader import StoredAudio
from app.services.emotion_analysis_service import analyze_emotion
from app.services.prosody_service import build_prosody_summary


def build_analysis_response(
    *,
    stored_audio: StoredAudio,
    acoustic_metrics: AcousticMetrics,
    transcription: Transcription,
    language: str,
    use_external_ai: bool,
    interpretation_style: InterpretationStyle,
    learning_examples: list[LearningExampleReference] | None = None,
    settings: Settings | None = None,
) -> AudioAnalysisResponse:
    settings = settings or get_settings()
    analysis_id = str(uuid4())
    created_at = datetime.now(timezone.utc)

    emotion_analysis = analyze_emotion(
        transcription=transcription,
        acoustic_metrics=acoustic_metrics,
        language=language,
        interpretation_style=interpretation_style,
        use_external_ai=use_external_ai,
        learning_examples=learning_examples or [],
        settings=settings,
    )
    prosody_summary = build_prosody_summary(
        acoustic_metrics,
        speech_rate_wpm=transcription.words_per_minute,
        calmness_score=emotion_analysis.emotion_summary.calmness_score or 0.0,
        tension_score=emotion_analysis.emotion_summary.tension_score or 0.0,
    )

    return AudioAnalysisResponse(
        analysis_id=analysis_id,
        metadata=AnalysisMetadata(
            file_name=stored_audio.original_file_name,
            file_hash=stored_audio.file_hash,
            language=language,
            duration_seconds=acoustic_metrics.duration_seconds,
            audio_duration_seconds=acoustic_metrics.duration_seconds,
            processing_version=settings.app_version,
            external_ai_used=emotion_analysis.external_ai_used,
            created_at=created_at,
        ),
        status=ProcessingStatus(
            acoustic_metrics_status="real",
            transcription_status="real",
            emotion_status=emotion_analysis.emotion_status,
            emotion_analysis_source=emotion_analysis.emotion_analysis_source,
        ),
        acoustic_metrics=acoustic_metrics,
        transcription=transcription,
        annotated_transcription=emotion_analysis.annotated_transcription,
        prosody_summary=prosody_summary,
        emotion_summary=emotion_analysis.emotion_summary,
        important_observations=emotion_analysis.important_observations,
        recommended_context_for_ai_agent=emotion_analysis.recommended_context_for_ai_agent,
        emotion_evidence=emotion_analysis.emotion_evidence,
        emotion_debug=emotion_analysis.emotion_debug,
        emotion_comparison=emotion_analysis.emotion_comparison,
        learning_examples_used=emotion_analysis.learning_examples_used,
        learning_influence_summary=emotion_analysis.learning_influence_summary,
        whether_learning_changed_result=emotion_analysis.whether_learning_changed_result,
        learning_adjustments=emotion_analysis.learning_adjustments,
        quality_warnings=emotion_analysis.quality_warnings,
        feedback=FeedbackInfo(
            feedback_url=f"/v1/analyses/{analysis_id}/feedback",
            message="Envie feedback positivo ou negativo para melhorar análises futuras.",
        ),
    )


build_mock_analysis_response = build_analysis_response
