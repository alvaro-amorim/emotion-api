from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlmodel import Session

from app.api.schemas import (
    AnalysisDebugResponse,
    AnalysisListResponse,
    AudioAnalysisResponse,
    InterpretationStyle,
    LearningContextResponse,
)
from app.core.config import get_settings
from app.db.repository import (
    create_audio_analysis,
    find_similar_learning_examples,
    get_learning_context_for_analysis,
    get_analysis_debug_response,
    get_audio_analysis_response,
    list_audio_analysis_responses,
)
from app.db.session import get_session
from app.services.audio_metrics_service import calculate_acoustic_metrics
from app.services.audio_preprocessor import standardize_audio
from app.services.audio_loader import save_upload_file
from app.services.response_builder import build_analysis_response
from app.services.transcription_service import transcribe_audio

router = APIRouter(prefix="/v1", tags=["audio"])


@router.post("/analyze-audio", response_model=AudioAnalysisResponse, status_code=201)
async def analyze_audio(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    use_external_ai: bool = Form(default=True),
    interpretation_style: InterpretationStyle = Form(default="interpretative"),
    session: Session = Depends(get_session),
) -> AudioAnalysisResponse:
    settings = get_settings()
    stored_audio = await save_upload_file(file, settings)
    processed_audio = standardize_audio(stored_audio, settings)
    acoustic_metrics = calculate_acoustic_metrics(processed_audio, settings)
    transcription = transcribe_audio(
        processed_audio,
        acoustic_metrics,
        language or settings.default_language,
        settings,
    )
    learning_examples = (
        find_similar_learning_examples(
            session,
            text=transcription.text,
            acoustic_metrics=acoustic_metrics.model_dump(mode="json"),
            speech_metrics={
                "word_count": transcription.word_count,
                "words_per_minute": transcription.words_per_minute,
                "estimated_speech_rate_label": transcription.estimated_speech_rate_label,
            },
            limit=settings.emotion_max_learning_examples,
            min_similarity=settings.emotion_learning_min_similarity,
        )
        if settings.emotion_use_learning_examples
        else []
    )
    response = build_analysis_response(
        stored_audio=stored_audio,
        acoustic_metrics=acoustic_metrics,
        transcription=transcription,
        language=language or settings.default_language,
        use_external_ai=use_external_ai,
        interpretation_style=interpretation_style,
        learning_examples=learning_examples,
        settings=settings,
    )
    return create_audio_analysis(session, response)


@router.get("/analyses", response_model=AnalysisListResponse)
def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> AnalysisListResponse:
    return list_audio_analysis_responses(session, limit=limit, offset=offset)


@router.get("/analyses/{analysis_id}", response_model=AudioAnalysisResponse)
def get_analysis(
    analysis_id: str,
    session: Session = Depends(get_session),
) -> AudioAnalysisResponse:
    return get_audio_analysis_response(session, analysis_id)


@router.get("/analyses/{analysis_id}/debug", response_model=AnalysisDebugResponse)
def get_analysis_debug(
    analysis_id: str,
    session: Session = Depends(get_session),
) -> AnalysisDebugResponse:
    return get_analysis_debug_response(session, analysis_id)


@router.get("/analyses/{analysis_id}/learning-context", response_model=LearningContextResponse)
def get_analysis_learning_context(
    analysis_id: str,
    limit: int = Query(default=3, ge=1, le=20),
    session: Session = Depends(get_session),
) -> LearningContextResponse:
    settings = get_settings()
    return get_learning_context_for_analysis(
        session,
        analysis_id=analysis_id,
        limit=limit,
        min_similarity=settings.emotion_learning_min_similarity,
    )
