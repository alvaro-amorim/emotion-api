from __future__ import annotations

from pydantic import BaseModel

from app.core.config import Settings


class EmotionHeuristicWeights(BaseModel):
    text_urgency_weight: float
    text_negative_weight: float
    high_volume_weight: float
    low_volume_weight: float
    silence_ratio_weight: float
    speech_rate_weight: float
    peak_volume_weight: float
    learning_example_weight: float
    cohere_weight: float
    fallback_weight: float

    high_silence_ratio_threshold: float
    low_wpm_threshold: float
    high_wpm_threshold: float
    high_peak_threshold: float
    low_volume_threshold: float
    learning_min_similarity: float


def get_emotion_heuristic_weights(settings: Settings) -> EmotionHeuristicWeights:
    return EmotionHeuristicWeights(
        text_urgency_weight=settings.emotion_text_urgency_weight,
        text_negative_weight=settings.emotion_text_negative_weight,
        high_volume_weight=settings.emotion_high_volume_weight,
        low_volume_weight=settings.emotion_low_volume_weight,
        silence_ratio_weight=settings.emotion_silence_ratio_weight,
        speech_rate_weight=settings.emotion_speech_rate_weight,
        peak_volume_weight=settings.emotion_peak_volume_weight,
        learning_example_weight=settings.emotion_learning_example_weight,
        cohere_weight=settings.emotion_cohere_weight,
        fallback_weight=settings.emotion_fallback_weight,
        high_silence_ratio_threshold=settings.emotion_high_silence_ratio_threshold,
        low_wpm_threshold=settings.emotion_low_wpm_threshold,
        high_wpm_threshold=settings.emotion_high_wpm_threshold,
        high_peak_threshold=settings.emotion_high_peak_threshold,
        low_volume_threshold=settings.emotion_low_volume_threshold,
        learning_min_similarity=settings.emotion_learning_min_similarity,
    )
