from sqlmodel import Session

from app.api.schemas import (
    LearningExampleResponse,
    LearningExamplesListResponse,
    LearningExampleUpdateRequest,
)
from app.db.repository import list_learning_examples, update_learning_example


def get_learning_examples(
    session: Session,
    *,
    approved_only: bool | None = None,
    limit: int = 100,
    corrected_emotion: str | None = None,
    source_analysis_id: str | None = None,
) -> LearningExamplesListResponse:
    return list_learning_examples(
        session,
        approved_only=approved_only,
        limit=limit,
        corrected_emotion=corrected_emotion,
        source_analysis_id=source_analysis_id,
    )


def patch_learning_example(
    session: Session,
    example_id: int,
    payload: LearningExampleUpdateRequest,
) -> LearningExampleResponse | None:
    return update_learning_example(session, example_id, payload)
