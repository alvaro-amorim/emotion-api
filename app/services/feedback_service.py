from sqlmodel import Session

from app.api.schemas import EmotionFeedbackRequest, FeedbackResponse
from app.db.repository import save_feedback


def register_feedback(
    session: Session,
    analysis_id: str,
    payload: EmotionFeedbackRequest,
) -> FeedbackResponse:
    return save_feedback(session, analysis_id, payload)

