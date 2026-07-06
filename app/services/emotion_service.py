"""Compatibility exports for emotion analysis services."""

from app.services.emotion_analysis_service import analyze_emotion, build_local_emotion_analysis

__all__ = ["analyze_emotion", "build_local_emotion_analysis"]
