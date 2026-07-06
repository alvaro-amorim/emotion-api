from app.api.schemas import AcousticMetrics, EmphasisWord, ProsodySummary


def build_prosody_summary(
    acoustic_metrics: AcousticMetrics,
    *,
    speech_rate_wpm: float = 0.0,
    calmness_score: float = 0.0,
    tension_score: float = 0.0,
) -> ProsodySummary:
    return ProsodySummary(
        speech_rate_wpm=speech_rate_wpm,
        pace="slow" if speech_rate_wpm < 110 else "fast" if speech_rate_wpm > 170 else "normal",
        avg_volume_db=acoustic_metrics.avg_volume_db,
        max_volume_db=acoustic_metrics.peak_volume_db,
        volume_variance=acoustic_metrics.volume_variance,
        pause_ratio=acoustic_metrics.silence_ratio,
        emphasis_words=[
            EmphasisWord(
                word="não",
                start=3.21,
                end=3.45,
                emphasis_score=0.82,
                reason="mock temporário até a transcrição real com timestamps por palavra",
            ),
            EmphasisWord(
                word="resolver",
                start=9.94,
                end=10.72,
                emphasis_score=0.73,
                reason="mock temporário até a análise de ênfase por palavra",
            ),
        ],
        calmness_score=calmness_score,
        tension_score=tension_score,
    )


def build_mock_prosody_summary(acoustic_metrics: AcousticMetrics) -> ProsodySummary:
    return build_prosody_summary(acoustic_metrics)
