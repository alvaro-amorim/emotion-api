import pytest

from app.api.schemas import (
    AcousticMetrics,
    LearningExampleReference,
    PeakEvent,
    Transcription,
    TranscriptionSegment,
    VolumeTimelinePoint,
)
from app.core.config import Settings
from app.services.cohere_service import CohereAnalysisError
from app.services.emotion_analysis_service import analyze_emotion, build_local_emotion_analysis


def _settings(**overrides) -> Settings:
    values = {
        "app_name": "Audio Emotion API",
        "app_env": "test",
        "app_debug": False,
        "app_version": "0.5.0",
        "database_url": "sqlite:///./test.db",
        "cohere_api_key": "",
        "cohere_model": "command-a-03-2025",
        "cohere_chat_model": "command-a-03-2025",
        "cohere_enabled": False,
        "use_cohere": False,
        "emotion_analysis_provider": "hybrid",
        "emotion_use_learning_examples": True,
        "emotion_max_learning_examples": 3,
        "emotion_confidence_threshold": 0.50,
        "emotion_learning_min_similarity": 0.20,
        "emotion_learning_example_weight": 0.25,
        "emotion_text_urgency_weight": 0.14,
        "emotion_text_negative_weight": 0.12,
        "emotion_high_volume_weight": 0.12,
        "emotion_low_volume_weight": 0.10,
        "emotion_silence_ratio_weight": 0.15,
        "emotion_speech_rate_weight": 0.10,
        "emotion_peak_volume_weight": 0.12,
        "emotion_cohere_weight": 0.65,
        "emotion_fallback_weight": 0.35,
        "emotion_high_silence_ratio_threshold": 0.35,
        "emotion_low_wpm_threshold": 85.0,
        "emotion_high_wpm_threshold": 150.0,
        "emotion_high_peak_threshold": -8.0,
        "emotion_low_volume_threshold": -30.0,
        "max_audio_duration_seconds": 600,
        "max_audio_file_size_mb": 100,
        "default_language": "pt-BR",
        "allowed_audio_extensions": (".mp3", ".wav", ".m4a", ".webm", ".ogg"),
        "transcription_provider": "local",
        "local_transcription_engine": "faster-whisper",
        "whisper_model_size": "tiny",
        "whisper_device": "cpu",
        "whisper_compute_type": "int8",
        "storage_dir": "storage",
        "audio_storage_dir": "storage/audio",
        "processed_audio_dir": "storage/processed",
    }
    values.update(overrides)
    return Settings(**values)


def _transcription(text: str, words_per_minute: float = 120.0) -> Transcription:
    return Transcription(
        text=text,
        segments=[TranscriptionSegment(id=0, start=0.0, end=4.0, text=text, confidence=0.9)],
        words=[],
        transcription_engine="faster-whisper",
        transcription_model="tiny",
        detected_language="pt",
        word_count=len(text.split()),
        words_per_minute=words_per_minute,
        estimated_speech_rate_label="normal",
        average_word_duration_ms=None,
    )


def _metrics(
    *,
    avg_volume_db: float = -24.0,
    peak_volume_db: float = -6.0,
    silence_ratio: float = 0.18,
) -> AcousticMetrics:
    return AcousticMetrics(
        duration_seconds=4.0,
        sample_rate=16000,
        avg_volume_db=avg_volume_db,
        peak_volume_db=peak_volume_db,
        volume_variance=420.0,
        dynamic_range_db=32.0,
        silence_count=1,
        total_silence_duration_seconds=0.7,
        silence_ratio=silence_ratio,
        longest_silence_seconds=0.7,
        estimated_speech_duration_seconds=3.3,
        peak_count=2,
        peak_events=[PeakEvent(time_seconds=1.0, volume_db=peak_volume_db, intensity_label="high")],
        volume_timeline=[VolumeTimelinePoint(start_seconds=0.0, end_seconds=0.5, volume_db=-20.0)],
        is_mostly_silent=False,
        audio_quality_warning=None,
        analysis_window_seconds=0.5,
    )


def test_local_fallback_returns_valid_emotion_structure():
    result = build_local_emotion_analysis(
        transcription=_transcription("Eu preciso resolver isso agora. O problema esta errado."),
        acoustic_metrics=_metrics(),
        language="pt-BR",
        interpretation_style="interpretative",
        settings=_settings(),
    )

    assert result.emotion_status == "fallback_local"
    assert result.emotion_analysis_source == "local_heuristics"
    assert result.emotion_summary.primary_emotion in {"urgencia", "preocupacao"}
    assert result.emotion_summary.confidence_score >= 0.5
    assert result.emotion_evidence
    assert result.emotion_debug.fallback_used is True
    assert result.emotion_debug.cohere_attempted is False
    assert result.emotion_comparison.agreement_level == "local_only"
    assert result.emotion_comparison.local_primary_emotion == result.emotion_summary.primary_emotion
    assert "[emoção:" in result.annotated_transcription.text


def test_cohere_failure_falls_back_to_local(monkeypatch: pytest.MonkeyPatch):
    def fail_cohere(*, prompt, settings):
        raise CohereAnalysisError("forced failure")

    monkeypatch.setattr(
        "app.services.emotion_analysis_service.generate_cohere_emotion_analysis",
        fail_cohere,
    )

    result = analyze_emotion(
        transcription=_transcription("Eu preciso de uma resposta rapida agora."),
        acoustic_metrics=_metrics(),
        language="pt-BR",
        interpretation_style="interpretative",
        use_external_ai=True,
        settings=_settings(cohere_api_key="fake-key", cohere_enabled=True, use_cohere=True),
    )

    assert result.emotion_status == "fallback_local"
    assert result.emotion_analysis_source == "local_heuristics"
    assert result.external_ai_used is False
    assert result.quality_warnings
    assert result.emotion_debug.cohere_attempted is True
    assert result.emotion_debug.cohere_success is False
    assert result.emotion_debug.fallback_used is True
    assert result.emotion_debug.fallback_reason == "cohere_request_failed"
    assert result.emotion_comparison.agreement_level == "local_only"


def test_mocked_cohere_response_is_normalized(monkeypatch: pytest.MonkeyPatch):
    def fake_cohere(*, prompt, settings):
        return {
            "annotated_transcription": (
                "Eu preciso agora [emoção: urgencia | tom: firme | observação: termos de urgencia]."
            ),
            "emotion_summary": {
                "primary_emotion": "urgencia",
                "secondary_emotions": ["preocupacao"],
                "implicit_emotion": "necessidade de resposta rapida",
                "emotional_tone": "firme",
                "interlocutor_calmness": "pouco calmo",
                "calmness_level": "baixo",
                "urgency_level": "alto",
                "intention": "solicitacao tecnica urgente",
                "calmness_score": 0.25,
                "tension_score": 0.72,
                "confidence_score": 0.81,
                "interpretation_summary": "Urgencia sustentada pelo texto.",
            },
            "important_observations": ["Ha termos de urgencia."],
            "recommended_context_for_ai_agent": "Responder com passos claros.",
            "emotion_evidence": [
                {
                    "type": "text",
                    "signal": "termos de urgencia",
                    "value": "preciso, agora",
                    "impact": "aumenta urgencia",
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.emotion_analysis_service.generate_cohere_emotion_analysis",
        fake_cohere,
    )

    result = analyze_emotion(
        transcription=_transcription("Eu preciso de uma resposta rapida agora."),
        acoustic_metrics=_metrics(),
        language="pt-BR",
        interpretation_style="interpretative",
        use_external_ai=True,
        settings=_settings(cohere_api_key="fake-key", cohere_enabled=True, use_cohere=True),
    )

    assert result.emotion_status == "real"
    assert result.emotion_analysis_source == "cohere"
    assert result.external_ai_used is True
    assert result.emotion_summary.analysis_model == "command-a-03-2025"
    assert result.emotion_evidence[0].signal == "termos de urgencia"
    assert result.emotion_debug.cohere_attempted is True
    assert result.emotion_debug.cohere_success is True
    assert result.emotion_debug.fallback_used is False
    assert result.emotion_debug.local_fallback_result["primary_emotion"]
    assert result.emotion_debug.cohere_result_raw_excerpt
    assert result.emotion_comparison.cohere_primary_emotion == "urgencia"
    assert result.emotion_comparison.agreement_level in {"full", "partial", "different"}


def test_use_cohere_false_debug_explains_local_fallback():
    result = analyze_emotion(
        transcription=_transcription("Eu preciso de uma resposta rapida agora."),
        acoustic_metrics=_metrics(),
        language="pt-BR",
        interpretation_style="interpretative",
        use_external_ai=True,
        settings=_settings(cohere_api_key="fake-key", cohere_enabled=True, use_cohere=False),
    )

    assert result.emotion_status == "fallback_local"
    assert result.emotion_debug.fallback_used is True
    assert result.emotion_debug.fallback_reason == "USE_COHERE=false"
    assert result.emotion_comparison.agreement_level == "local_only"


def test_learning_examples_influence_local_fallback_debug():
    learning_example = LearningExampleReference(
        id=10,
        source_analysis_id="analysis-10",
        text_excerpt="talvez eu precise tentar de novo com calma",
        corrected_prediction={"primary_emotion": "inseguranca", "tone": "pausado e hesitante"},
        similarity_score=0.92,
        matched_terms=["talvez", "precise", "tentar"],
        metric_similarity=0.8,
        text_similarity=0.7,
        recency_score=1.0,
        correction_summary="correcao: inseguranca; tom: pausado e hesitante",
        reason_used="texto=0.7; metricas=0.8",
        corrected_primary_emotion="inseguranca",
        corrected_tone="pausado e hesitante",
    )

    result = build_local_emotion_analysis(
        transcription=_transcription("Talvez eu precise tentar de novo com calma.", words_per_minute=80),
        acoustic_metrics=_metrics(avg_volume_db=-32.0, peak_volume_db=-18.0, silence_ratio=0.42),
        language="pt-BR",
        interpretation_style="interpretative",
        learning_examples=[learning_example],
        settings=_settings(emotion_learning_example_weight=0.8),
    )

    assert result.learning_influence_summary
    assert result.emotion_debug.learning_influence_applied is True
    assert result.emotion_debug.learning_examples_used_count == 1
    assert result.emotion_debug.top_learning_examples[0]["id"] == 10
    assert result.emotion_debug.heuristic_scores["before_learning"]
    assert result.emotion_debug.heuristic_scores["after_learning"]
    assert result.emotion_comparison.learning_changed_local_result is result.whether_learning_changed_result


def test_cohere_prompt_receives_similar_learning_examples(monkeypatch: pytest.MonkeyPatch):
    captured_prompt = ""

    def fake_cohere(*, prompt, settings):
        nonlocal captured_prompt
        captured_prompt = prompt
        return {
            "annotated_transcription": "Talvez eu tente [emoção: inseguranca | tom: hesitante | observação: exemplo anterior parecido].",
            "emotion_summary": {
                "primary_emotion": "inseguranca",
                "secondary_emotions": ["duvida"],
                "implicit_emotion": "duvida sobre a explicacao",
                "emotional_tone": "hesitante",
                "interlocutor_calmness": "moderadamente calmo",
                "calmness_level": "medio",
                "urgency_level": "baixo",
                "intention": "pedido de ajuda",
                "calmness_score": 0.62,
                "tension_score": 0.34,
                "confidence_score": 0.76,
                "interpretation_summary": "Exemplo humano anterior orientou a leitura.",
            },
            "important_observations": ["Exemplo anterior semelhante foi considerado."],
            "recommended_context_for_ai_agent": "Responder com acolhimento.",
            "emotion_evidence": [
                {
                    "type": "learning",
                    "signal": "learning_examples",
                    "value": "exemplo aprovado",
                    "impact": "orienta sem forcar a conclusao",
                }
            ],
        }

    monkeypatch.setattr(
        "app.services.emotion_analysis_service.generate_cohere_emotion_analysis",
        fake_cohere,
    )

    result = analyze_emotion(
        transcription=_transcription("Talvez eu precise tentar de novo."),
        acoustic_metrics=_metrics(avg_volume_db=-31.0, peak_volume_db=-18.0, silence_ratio=0.4),
        language="pt-BR",
        interpretation_style="interpretative",
        use_external_ai=True,
        learning_examples=[
            LearningExampleReference(
                id=7,
                source_analysis_id="analysis-7",
                text_excerpt="talvez eu precise tentar de novo",
                corrected_prediction={"primary_emotion": "inseguranca"},
                similarity_score=0.88,
                corrected_primary_emotion="inseguranca",
            )
        ],
        settings=_settings(cohere_api_key="fake-key", cohere_enabled=True, use_cohere=True),
    )

    assert result.emotion_status == "real"
    assert '"learning_examples"' in captured_prompt
    assert "feedbacks humanos anteriores" in captured_prompt
    assert "ignore exemplos que nao se apliquem" in captured_prompt
    assert "inseguranca" in captured_prompt
