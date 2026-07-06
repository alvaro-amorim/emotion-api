from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from app.api.schemas import (
    EmotionFeedbackRequest,
    FeedbackResponse,
    LearningExampleResponse,
    LearningExampleUpdateRequest,
    LearningExamplesListResponse,
)
from app.core.security import require_api_key
from app.db.session import get_session
from app.services.feedback_service import register_feedback
from app.services.learning_service import get_learning_examples, patch_learning_example

router = APIRouter(prefix="/v1", tags=["feedback"], dependencies=[Depends(require_api_key)])


@router.post(
    "/analyses/{analysis_id}/feedback",
    response_model=FeedbackResponse,
    status_code=201,
)
def submit_feedback(
    analysis_id: str,
    payload: EmotionFeedbackRequest,
    session: Session = Depends(get_session),
) -> FeedbackResponse:
    return register_feedback(session, analysis_id, payload)


@router.get("/learning/examples", response_model=LearningExamplesListResponse)
def list_learning_examples_endpoint(
    approved_only: bool | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    corrected_emotion: str | None = Query(default=None),
    source_analysis_id: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> LearningExamplesListResponse:
    return get_learning_examples(
        session,
        approved_only=approved_only,
        limit=limit,
        corrected_emotion=corrected_emotion,
        source_analysis_id=source_analysis_id,
    )


@router.patch("/learning/examples/{example_id}", response_model=LearningExampleResponse)
def update_learning_example_endpoint(
    example_id: int,
    payload: LearningExampleUpdateRequest,
    session: Session = Depends(get_session),
) -> LearningExampleResponse:
    example = patch_learning_example(session, example_id, payload)
    if example is None:
        raise HTTPException(status_code=404, detail="Learning example nao encontrado.")
    return example
