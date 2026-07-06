from __future__ import annotations

import json
import math
import re
import unicodedata

from pydantic import BaseModel, Field

from app.api.schemas import (
    AcousticMetrics,
    AnnotatedTranscription,
    EmotionComparison,
    EmotionDebug,
    EmotionEvidence,
    EmotionSummary,
    InterpretationStyle,
    LearningExampleReference,
    Transcription,
)
from app.core.config import Settings, get_settings
from app.core.emotion_weights import EmotionHeuristicWeights, get_emotion_heuristic_weights
from app.services.cohere_service import CohereAnalysisError, generate_cohere_emotion_analysis, should_attempt_external_ai


LOCAL_MODEL_NAME = "local-heuristics-v1"


class EmotionAnalysisResult(BaseModel):
    emotion_status: str
    emotion_analysis_source: str
    emotion_analysis_model: str
    external_ai_used: bool
    emotion_summary: EmotionSummary
    annotated_transcription: AnnotatedTranscription
    important_observations: list[str]
    recommended_context_for_ai_agent: str
    emotion_evidence: list[EmotionEvidence]
    emotion_debug: EmotionDebug = Field(default_factory=EmotionDebug)
    emotion_comparison: EmotionComparison = Field(default_factory=EmotionComparison)
    learning_examples_used: list[LearningExampleReference] = Field(default_factory=list)
    learning_influence_summary: str | None = None
    whether_learning_changed_result: bool = False
    learning_adjustments: list[str] = Field(default_factory=list)
    quality_warnings: list[str] = Field(default_factory=list)


def analyze_emotion(
    *,
    transcription: Transcription,
    acoustic_metrics: AcousticMetrics,
    language: str,
    interpretation_style: InterpretationStyle,
    use_external_ai: bool,
    learning_examples: list[LearningExampleReference] | None = None,
    settings: Settings | None = None,
) -> EmotionAnalysisResult:
    settings = settings or get_settings()
    learning_examples = learning_examples or []
    local_result = build_local_emotion_analysis(
        transcription=transcription,
        acoustic_metrics=acoustic_metrics,
        language=language,
        interpretation_style=interpretation_style,
        learning_examples=learning_examples,
        settings=settings,
    )

    skip_reason = _external_ai_skip_reason(
        requested_by_user=use_external_ai,
        transcription_text=transcription.text,
        settings=settings,
    )
    if skip_reason is not None or not should_attempt_external_ai(
        requested_by_user=use_external_ai,
        transcription_text=transcription.text,
        settings=settings,
    ):
        if use_external_ai and skip_reason not in {"use_external_ai=false", "empty_transcription"}:
            local_result.quality_warnings.append(
                "Cohere nao configurada ou desativada; analise emocional gerada por fallback local."
            )
        _attach_debug_and_comparison(
            result=local_result,
            local_result=local_result,
            cohere_result=None,
            settings=settings,
            cohere_attempted=False,
            cohere_success=False,
            fallback_used=True,
            fallback_reason=skip_reason or "external_ai_not_attempted",
            cohere_raw_payload=None,
            learning_examples_count=len(learning_examples),
        )
        return local_result

    prompt = build_cohere_prompt(
        transcription=transcription,
        acoustic_metrics=acoustic_metrics,
        local_result=local_result,
        learning_examples=learning_examples,
        language=language,
        interpretation_style=interpretation_style,
    )
    try:
        cohere_payload = generate_cohere_emotion_analysis(prompt=prompt, settings=settings)
        result = _result_from_cohere_payload(
            payload=cohere_payload,
            fallback=local_result,
            language=language,
            interpretation_style=interpretation_style,
            model=settings.cohere_chat_model,
        )
        _attach_debug_and_comparison(
            result=result,
            local_result=local_result,
            cohere_result=result,
            settings=settings,
            cohere_attempted=True,
            cohere_success=True,
            fallback_used=False,
            fallback_reason=None,
            cohere_raw_payload=cohere_payload,
            learning_examples_count=len(learning_examples),
        )
        return result
    except CohereAnalysisError:
        local_result.quality_warnings.append(
            "Falha ou indisponibilidade da Cohere; analise emocional gerada por fallback local."
        )
        _attach_debug_and_comparison(
            result=local_result,
            local_result=local_result,
            cohere_result=None,
            settings=settings,
            cohere_attempted=True,
            cohere_success=False,
            fallback_used=True,
            fallback_reason="cohere_request_failed",
            cohere_raw_payload=None,
            learning_examples_count=len(learning_examples),
        )
        return local_result


def build_local_emotion_analysis(
    *,
    transcription: Transcription,
    acoustic_metrics: AcousticMetrics,
    language: str,
    interpretation_style: InterpretationStyle,
    learning_examples: list[LearningExampleReference] | None = None,
    settings: Settings | None = None,
) -> EmotionAnalysisResult:
    settings = settings or get_settings()
    weights = get_emotion_heuristic_weights(settings)
    learning_examples = learning_examples or []
    text = transcription.text.strip()
    normalized = _normalize_text(text)

    urgency_terms = _matched_terms(
        normalized,
        [
            "preciso",
            "preciso resolver",
            "resolver isso agora",
            "urgente",
            "rapida",
            "rapido",
            "nao pode esperar",
        ],
    )
    negative_terms = _matched_terms(
        normalized,
        ["problema", "errado", "nao funciona", "nao consegui", "nao entende", "continua acontecendo"],
    )
    uncertainty_terms = _matched_terms(
        normalized,
        ["nao tenho certeza", "talvez", "inseguro", "duvida", "explicar direito", "tentar de novo"],
    )
    calm_terms = _matched_terms(normalized, ["calma", "calmo", "tranquilo", "tranquila", "sem pressa"])

    silence_ratio = acoustic_metrics.silence_ratio
    avg_volume = acoustic_metrics.avg_volume_db
    peak_volume = acoustic_metrics.peak_volume_db
    wpm = transcription.words_per_minute

    urgency_score = _clamp(
        0.15
        + weights.text_urgency_weight * len(urgency_terms)
        + (0.15 if "resolver isso agora" in urgency_terms else 0.0)
        + (weights.peak_volume_weight if peak_volume > weights.high_peak_threshold else 0.0)
        + (weights.speech_rate_weight if wpm > weights.high_wpm_threshold else 0.0)
    )
    uncertainty_score = _clamp(
        0.12
        + 0.16 * len(uncertainty_terms)
        + (weights.silence_ratio_weight if silence_ratio >= weights.high_silence_ratio_threshold else 0.0)
        + (weights.low_volume_weight if avg_volume < weights.low_volume_threshold else 0.0)
    )
    concern_score = _clamp(
        0.18
        + weights.text_negative_weight * len(negative_terms)
        + 0.06 * len(urgency_terms)
        + (0.08 if acoustic_metrics.volume_variance > 300 else 0.0)
    )
    calm_score = _clamp(
        0.42
        + 0.10 * len(calm_terms)
        + (0.12 if weights.low_wpm_threshold <= wpm <= 135 else 0.0)
        + (0.10 if silence_ratio < 0.25 else 0.0)
        - (0.20 if urgency_score > 0.55 else 0.0)
        - (0.12 if concern_score > 0.60 else 0.0)
    )
    tension_score = _clamp(
        0.20
        + 0.30 * urgency_score
        + 0.25 * concern_score
        + (0.15 if acoustic_metrics.volume_variance > 350 else 0.0)
        - (0.15 if calm_score > 0.65 else 0.0)
    )

    scores_before_learning = {
        "urgencia": round(urgency_score, 3),
        "inseguranca": round(uncertainty_score, 3),
        "preocupacao": round(concern_score, 3),
        "calma": round(calm_score, 3),
        "tensao": round(tension_score, 3),
    }

    primary_before_learning = _choose_primary_emotion(
        urgency_score=urgency_score,
        uncertainty_score=uncertainty_score,
        concern_score=concern_score,
        calm_score=calm_score,
    )
    primary_emotion = primary_before_learning
    secondary_emotions = _secondary_emotions(
        primary_emotion=primary_emotion,
        urgency_score=urgency_score,
        uncertainty_score=uncertainty_score,
        concern_score=concern_score,
        calm_score=calm_score,
    )
    urgency_level = _level(urgency_score, low="baixo", mid="medio", high="alto")
    calmness_level = _level(calm_score, low="baixo", mid="medio", high="alto")
    emotional_tone = _tone(primary_emotion, urgency_score, calm_score, uncertainty_score)
    confidence_score = _confidence_score(
        matched_signal_count=len(urgency_terms) + len(negative_terms) + len(uncertainty_terms) + len(calm_terms),
        acoustic_metrics=acoustic_metrics,
        transcription=transcription,
        settings=settings,
    )
    learning_influence = _apply_learning_examples(
        primary_emotion=primary_emotion,
        secondary_emotions=secondary_emotions,
        confidence_score=confidence_score,
        scores=scores_before_learning,
        learning_examples=learning_examples,
        weights=weights,
    )
    primary_emotion = learning_influence["primary_emotion"]
    secondary_emotions = learning_influence["secondary_emotions"]
    confidence_score = learning_influence["confidence_score"]
    scores_after_learning = learning_influence["scores_after_learning"]
    evidence = _build_evidence(
        urgency_terms=urgency_terms,
        negative_terms=negative_terms,
        uncertainty_terms=uncertainty_terms,
        calm_terms=calm_terms,
        acoustic_metrics=acoustic_metrics,
        transcription=transcription,
    )
    if learning_influence["learning_influence_applied"]:
        evidence.append(
            EmotionEvidence(
                type="learning",
                signal="learning_examples",
                value=learning_influence["top_learning_examples"],
                impact=learning_influence["learning_influence_summary"],
            )
        )
    observations = _observations(
        primary_emotion=primary_emotion,
        urgency_level=urgency_level,
        calmness_level=calmness_level,
        evidence=evidence,
        learning_examples=learning_examples,
    )
    if learning_influence["learning_influence_summary"]:
        observations.append(learning_influence["learning_influence_summary"])
    interpretation_summary = (
        f"Analise interpretativa local: emocao primaria provavel '{primary_emotion}', "
        f"urgencia {urgency_level} e calma {calmness_level}, com base em texto, volume, pausas e ritmo."
    )
    recommended_context = _recommended_context(primary_emotion, urgency_level, calmness_level)
    annotated = _annotate_transcription(
        transcription=transcription,
        primary_emotion=primary_emotion,
        emotional_tone=emotional_tone,
        evidence=evidence,
        language=language,
        source="local_heuristics",
    )

    summary = EmotionSummary(
        primary_emotion=primary_emotion,
        secondary_emotions=secondary_emotions,
        implicit_emotion=_implicit_emotion(primary_emotion, uncertainty_score, concern_score),
        emotional_tone=emotional_tone,
        interlocutor_calmness=_calmness_phrase(calmness_level),
        calmness_level=calmness_level,
        urgency_level=urgency_level,
        intention=_intention(urgency_score, uncertainty_score, concern_score),
        calmness_score=round(calm_score, 3),
        tension_score=round(tension_score, 3),
        confidence_score=confidence_score,
        interpretation_style=interpretation_style,
        interpretation_summary=interpretation_summary,
        analysis_source="local_heuristics",
        analysis_model=LOCAL_MODEL_NAME,
        analysis_status="fallback_local",
    )

    result = EmotionAnalysisResult(
        emotion_status="fallback_local",
        emotion_analysis_source="local_heuristics",
        emotion_analysis_model=LOCAL_MODEL_NAME,
        external_ai_used=False,
        emotion_summary=summary,
        annotated_transcription=annotated,
        important_observations=observations,
        recommended_context_for_ai_agent=recommended_context,
        emotion_evidence=evidence,
        learning_examples_used=learning_examples,
        learning_influence_summary=learning_influence["learning_influence_summary"],
        whether_learning_changed_result=learning_influence["whether_learning_changed_result"],
        learning_adjustments=learning_influence["learning_adjustments"],
        quality_warnings=[],
    )
    _attach_debug_and_comparison(
        result=result,
        local_result=result,
        cohere_result=None,
        settings=settings,
        cohere_attempted=False,
        cohere_success=False,
        fallback_used=True,
        fallback_reason="local_fallback",
        cohere_raw_payload=None,
        learning_examples_count=len(learning_examples),
        debug_context={
            "learning_examples_requested": settings.emotion_use_learning_examples,
            "learning_examples_found": len(learning_examples),
            "learning_examples_used_count": len(learning_examples),
            "learning_min_similarity": weights.learning_min_similarity,
            "top_learning_examples": learning_influence["top_learning_examples"],
            "learning_influence_applied": learning_influence["learning_influence_applied"],
            "learning_influence_summary": learning_influence["learning_influence_summary"],
            "whether_learning_changed_result": learning_influence["whether_learning_changed_result"],
            "learning_adjustments": learning_influence["learning_adjustments"],
            "heuristic_weights_snapshot": weights.model_dump(mode="json"),
            "heuristic_scores": {
                "before_learning": scores_before_learning,
                "after_learning": scores_after_learning,
                "matched_terms": {
                    "urgency": urgency_terms,
                    "negative": negative_terms,
                    "uncertainty": uncertainty_terms,
                    "calm": calm_terms,
                },
            },
            "final_decision_factors": _final_decision_factors(
                primary_before_learning=primary_before_learning,
                primary_after_learning=primary_emotion,
                scores_after_learning=scores_after_learning,
                learning_influence_summary=learning_influence["learning_influence_summary"],
            ),
        },
    )
    return result


def build_cohere_prompt(
    *,
    transcription: Transcription,
    acoustic_metrics: AcousticMetrics,
    local_result: EmotionAnalysisResult,
    learning_examples: list[LearningExampleReference],
    language: str,
    interpretation_style: InterpretationStyle,
) -> str:
    payload = {
        "language": language,
        "interpretation_style": interpretation_style,
        "transcription": transcription.model_dump(mode="json"),
        "acoustic_metrics": acoustic_metrics.model_dump(mode="json"),
        "local_fallback_preview": {
            "emotion_summary": local_result.emotion_summary.model_dump(mode="json"),
            "emotion_evidence": [item.model_dump(mode="json") for item in local_result.emotion_evidence],
            "learning_influence_summary": local_result.learning_influence_summary,
            "whether_learning_changed_result": local_result.whether_learning_changed_result,
            "learning_adjustments": local_result.learning_adjustments,
        },
        "learning_examples": [item.model_dump(mode="json") for item in learning_examples],
    }
    return (
        "Voce e um analisador de emocao, intencao e tom de fala para audios em portugues brasileiro.\n"
        "A analise e interpretativa, nao uma certeza clinica ou psicologica.\n"
        "Use somente os dados fornecidos: transcricao, segmentos, palavras, metricas acusticas, ritmo, "
        "silencios, picos de volume e exemplos corrigidos anteriores.\n"
        "Os learning_examples sao feedbacks humanos anteriores aprovados para reutilizacao. "
        "Eles devem orientar a analise, mas nao devem forcar uma conclusao; ignore exemplos que nao se apliquem.\n"
        "Nao invente metricas. Nao diga que a emocao e certeza absoluta.\n"
        "Gere uma transcricao comentada preservando o texto real e usando comentarios no formato "
        "[emoção: ... | tom: ... | observação: ...].\n"
        "Retorne somente JSON valido com estes campos: annotated_transcription, emotion_summary, "
        "important_observations, recommended_context_for_ai_agent, emotion_evidence.\n"
        "emotion_summary deve conter: primary_emotion, secondary_emotions, implicit_emotion, "
        "emotional_tone, interlocutor_calmness, calmness_level, urgency_level, intention, "
        "calmness_score, tension_score, confidence_score, interpretation_summary.\n"
        "emotion_evidence deve ser uma lista de objetos com type, signal, value e impact.\n"
        f"Dados de entrada:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def _result_from_cohere_payload(
    *,
    payload: dict,
    fallback: EmotionAnalysisResult,
    language: str,
    interpretation_style: InterpretationStyle,
    model: str,
) -> EmotionAnalysisResult:
    summary_payload = payload.get("emotion_summary") if isinstance(payload.get("emotion_summary"), dict) else {}
    summary = EmotionSummary(
        primary_emotion=str(summary_payload.get("primary_emotion") or fallback.emotion_summary.primary_emotion),
        secondary_emotions=_string_list(
            summary_payload.get("secondary_emotions"),
            fallback.emotion_summary.secondary_emotions,
        ),
        implicit_emotion=str(summary_payload.get("implicit_emotion") or fallback.emotion_summary.implicit_emotion),
        emotional_tone=str(summary_payload.get("emotional_tone") or fallback.emotion_summary.emotional_tone),
        interlocutor_calmness=str(
            summary_payload.get("interlocutor_calmness") or fallback.emotion_summary.interlocutor_calmness
        ),
        calmness_level=str(summary_payload.get("calmness_level") or fallback.emotion_summary.calmness_level),
        urgency_level=str(summary_payload.get("urgency_level") or fallback.emotion_summary.urgency_level),
        intention=str(summary_payload.get("intention") or fallback.emotion_summary.intention),
        calmness_score=_number_or_default(
            summary_payload.get("calmness_score"),
            fallback.emotion_summary.calmness_score or 0.0,
        ),
        tension_score=_number_or_default(
            summary_payload.get("tension_score"),
            fallback.emotion_summary.tension_score or 0.0,
        ),
        confidence_score=_number_or_default(
            summary_payload.get("confidence_score"),
            fallback.emotion_summary.confidence_score,
        ),
        interpretation_style=interpretation_style,
        interpretation_summary=str(
            summary_payload.get("interpretation_summary") or fallback.emotion_summary.interpretation_summary
        ),
        analysis_source="cohere",
        analysis_model=model,
        analysis_status="success",
    )
    evidence = _evidence_from_payload(payload.get("emotion_evidence"), fallback.emotion_evidence)
    annotated_text = str(payload.get("annotated_transcription") or fallback.annotated_transcription.text)
    observations = _string_list(payload.get("important_observations"), fallback.important_observations)
    recommended_context = str(
        payload.get("recommended_context_for_ai_agent") or fallback.recommended_context_for_ai_agent
    )
    return EmotionAnalysisResult(
        emotion_status="real",
        emotion_analysis_source="cohere",
        emotion_analysis_model=model,
        external_ai_used=True,
        emotion_summary=summary,
        annotated_transcription=AnnotatedTranscription(
            text=annotated_text,
            language=language,
            analysis_source="cohere",
        ),
        important_observations=observations,
        recommended_context_for_ai_agent=recommended_context,
        emotion_evidence=evidence,
        learning_examples_used=fallback.learning_examples_used,
        learning_influence_summary=fallback.learning_influence_summary,
        whether_learning_changed_result=fallback.whether_learning_changed_result,
        learning_adjustments=fallback.learning_adjustments,
        quality_warnings=[],
    )


def _attach_debug_and_comparison(
    *,
    result: EmotionAnalysisResult,
    local_result: EmotionAnalysisResult,
    cohere_result: EmotionAnalysisResult | None,
    settings: Settings,
    cohere_attempted: bool,
    cohere_success: bool,
    fallback_used: bool,
    fallback_reason: str | None,
    cohere_raw_payload: dict | None,
    learning_examples_count: int,
    debug_context: dict | None = None,
) -> None:
    previous_debug = local_result.emotion_debug
    context = debug_context or {
        "learning_examples_requested": previous_debug.learning_examples_requested,
        "learning_examples_found": previous_debug.learning_examples_found,
        "learning_examples_used_count": previous_debug.learning_examples_used_count,
        "learning_min_similarity": previous_debug.learning_min_similarity,
        "top_learning_examples": previous_debug.top_learning_examples,
        "learning_influence_applied": previous_debug.learning_influence_applied,
        "learning_influence_summary": previous_debug.learning_influence_summary,
        "whether_learning_changed_result": previous_debug.whether_learning_changed_result,
        "learning_adjustments": previous_debug.learning_adjustments,
        "heuristic_weights_snapshot": previous_debug.heuristic_weights_snapshot,
        "heuristic_scores": previous_debug.heuristic_scores,
        "final_decision_factors": previous_debug.final_decision_factors,
    }
    result.emotion_debug = EmotionDebug(
        provider_requested=settings.emotion_analysis_provider,
        cohere_enabled=settings.external_ai_available,
        cohere_attempted=cohere_attempted,
        cohere_success=cohere_success,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        local_fallback_result=_local_result_summary(local_result),
        cohere_result_raw_excerpt=_safe_payload_excerpt(cohere_raw_payload),
        learning_examples_count=learning_examples_count,
        learning_examples_requested=context["learning_examples_requested"],
        learning_examples_found=context["learning_examples_found"],
        learning_examples_used_count=context["learning_examples_used_count"],
        learning_min_similarity=context["learning_min_similarity"],
        top_learning_examples=context["top_learning_examples"],
        learning_influence_applied=context["learning_influence_applied"],
        learning_influence_summary=context["learning_influence_summary"],
        whether_learning_changed_result=context["whether_learning_changed_result"],
        learning_adjustments=context["learning_adjustments"],
        heuristic_weights_snapshot=context["heuristic_weights_snapshot"],
        heuristic_scores=context["heuristic_scores"],
        final_decision_factors=context["final_decision_factors"],
        warnings=list(result.quality_warnings),
    )
    result.emotion_comparison = _build_comparison(
        local_result=local_result,
        cohere_result=cohere_result,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        debug_context=context,
    )


def _external_ai_skip_reason(
    *,
    requested_by_user: bool,
    transcription_text: str,
    settings: Settings,
) -> str | None:
    provider = settings.emotion_analysis_provider.strip().lower()
    if not requested_by_user:
        return "use_external_ai=false"
    if provider in {"local", "local_fallback", "local_heuristics"}:
        return f"EMOTION_ANALYSIS_PROVIDER={settings.emotion_analysis_provider}"
    if not transcription_text.strip():
        return "empty_transcription"
    if not settings.use_cohere:
        return "USE_COHERE=false"
    if not settings.cohere_enabled:
        return "COHERE_ENABLED=false"
    if not settings.cohere_api_key:
        return "COHERE_API_KEY empty"
    return None


def _local_result_summary(result: EmotionAnalysisResult) -> dict:
    summary = result.emotion_summary
    return {
        "primary_emotion": summary.primary_emotion,
        "secondary_emotions": summary.secondary_emotions,
        "emotional_tone": summary.emotional_tone,
        "urgency_level": summary.urgency_level,
        "calmness_level": summary.calmness_level,
        "calmness_score": summary.calmness_score,
        "tension_score": summary.tension_score,
        "confidence_score": summary.confidence_score,
        "analysis_source": result.emotion_analysis_source,
        "analysis_model": result.emotion_analysis_model,
    }


def _safe_payload_excerpt(payload: dict | None, max_chars: int = 800) -> str | None:
    if payload is None:
        return None
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return text[:max_chars] + ("..." if len(text) > max_chars else "")


def _build_comparison(
    *,
    local_result: EmotionAnalysisResult,
    cohere_result: EmotionAnalysisResult | None,
    fallback_used: bool,
    fallback_reason: str | None,
    debug_context: dict,
) -> EmotionComparison:
    local_primary = local_result.emotion_summary.primary_emotion
    local_before = debug_context.get("heuristic_scores", {}).get("before_learning", {})
    local_before_primary = _primary_from_scores(local_before) or local_primary
    learning_changed = bool(debug_context.get("whether_learning_changed_result"))
    if cohere_result is None:
        return EmotionComparison(
            local_before_learning=local_before_primary,
            local_after_learning=local_primary,
            local_primary_emotion=local_primary,
            cohere_primary_emotion=None,
            cohere_result=None,
            agreement_level="local_only" if fallback_used else "unavailable",
            learning_changed_local_result=learning_changed,
            differences=[
                f"Cohere nao gerou resultado; resultado final veio do fallback local ({fallback_reason})."
            ]
            if fallback_reason
            else ["Cohere nao gerou resultado para comparacao."],
        )

    cohere_primary = cohere_result.emotion_summary.primary_emotion
    local_primary_key = _normalize_label(local_primary)
    cohere_primary_key = _normalize_label(cohere_primary)
    local_secondary = {_normalize_label(item) for item in local_result.emotion_summary.secondary_emotions}
    cohere_secondary = {_normalize_label(item) for item in cohere_result.emotion_summary.secondary_emotions}

    if local_primary_key == cohere_primary_key:
        agreement_level = "full"
        differences = ["Fallback local e Cohere concordaram na emocao primaria."]
    elif cohere_primary_key in local_secondary or local_primary_key in cohere_secondary:
        agreement_level = "partial"
        differences = [
            f"Fallback local priorizou {local_primary}; Cohere priorizou {cohere_primary}, "
            "mas ha sobreposicao entre emocao primaria e secundaria."
        ]
    else:
        agreement_level = "different"
        differences = [
            f"Fallback local priorizou {local_primary}; Cohere priorizou {cohere_primary}."
        ]

    if local_result.emotion_summary.urgency_level != cohere_result.emotion_summary.urgency_level:
        differences.append(
            "Nivel de urgencia divergiu: "
            f"fallback={local_result.emotion_summary.urgency_level}, "
            f"cohere={cohere_result.emotion_summary.urgency_level}."
        )
    if local_result.emotion_summary.calmness_level != cohere_result.emotion_summary.calmness_level:
        differences.append(
            "Nivel de calma divergiu: "
            f"fallback={local_result.emotion_summary.calmness_level}, "
            f"cohere={cohere_result.emotion_summary.calmness_level}."
        )

    return EmotionComparison(
        local_before_learning=local_before_primary,
        local_after_learning=local_primary,
        local_primary_emotion=local_primary,
        cohere_primary_emotion=cohere_primary,
        cohere_result=cohere_primary,
        agreement_level=agreement_level,
        learning_changed_local_result=learning_changed,
        differences=differences,
    )


def _apply_learning_examples(
    *,
    primary_emotion: str,
    secondary_emotions: list[str],
    confidence_score: float,
    scores: dict[str, float],
    learning_examples: list[LearningExampleReference],
    weights: EmotionHeuristicWeights,
) -> dict:
    if not learning_examples:
        return {
            "primary_emotion": primary_emotion,
            "secondary_emotions": secondary_emotions,
            "confidence_score": confidence_score,
            "scores_after_learning": dict(scores),
            "learning_influence_applied": False,
            "learning_influence_summary": None,
            "whether_learning_changed_result": False,
            "learning_adjustments": [],
            "top_learning_examples": [],
        }

    scores_after = dict(scores)
    adjustments: list[str] = []
    top_examples: list[dict] = []
    emotion_votes: dict[str, float] = {}

    for example in learning_examples:
        corrected_emotion = _normalize_label(
            example.corrected_primary_emotion
            or example.corrected_prediction.get("primary_emotion")
            or ""
        )
        if not corrected_emotion:
            continue
        influence = round(example.similarity_score * weights.learning_example_weight, 3)
        if influence <= 0:
            continue
        emotion_votes[corrected_emotion] = emotion_votes.get(corrected_emotion, 0.0) + influence
        scores_after[corrected_emotion] = round(scores_after.get(corrected_emotion, 0.0) + influence, 3)
        top_examples.append(
            {
                "id": example.id,
                "source_analysis_id": example.source_analysis_id,
                "similarity_score": example.similarity_score,
                "matched_terms": example.matched_terms,
                "metric_similarity": example.metric_similarity,
                "text_similarity": example.text_similarity,
                "corrected_primary_emotion": example.corrected_primary_emotion
                or example.corrected_prediction.get("primary_emotion"),
                "corrected_tone": example.corrected_tone or example.corrected_prediction.get("tone"),
                "reason_used": example.reason_used,
            }
        )

    if not emotion_votes:
        return {
            "primary_emotion": primary_emotion,
            "secondary_emotions": secondary_emotions,
            "confidence_score": confidence_score,
            "scores_after_learning": scores_after,
            "learning_influence_applied": False,
            "learning_influence_summary": "Exemplos parecidos foram encontrados, mas nao tinham emocao corrigida reutilizavel.",
            "whether_learning_changed_result": False,
            "learning_adjustments": [],
            "top_learning_examples": top_examples[:3],
        }

    before_primary = primary_emotion
    after_primary = _primary_from_scores(scores_after) or primary_emotion
    changed = after_primary != _normalize_label(before_primary)
    if changed:
        adjustments.append(
            f"Resultado local ajustado de {before_primary} para {after_primary} por exemplos aprovados similares."
        )
    else:
        adjustments.append(
            f"Exemplos similares reforcaram ou contextualizaram a emocao local {primary_emotion}."
        )

    strongest_emotion, strongest_vote = max(emotion_votes.items(), key=lambda item: item[1])
    if strongest_emotion != _normalize_label(primary_emotion) and not changed:
        adjustments.append(
            f"Exemplos apontaram {strongest_emotion}, mas o score combinado nao superou a heuristica local."
        )
        confidence_score = round(max(0.35, confidence_score - 0.03), 3)
    else:
        confidence_score = round(_clamp(confidence_score + min(0.08, strongest_vote / 2), 0.35, 0.92), 3)

    secondary = list(dict.fromkeys([after_primary, *secondary_emotions, strongest_emotion]))
    secondary = [emotion for emotion in secondary if emotion != after_primary][:3] or ["neutralidade"]
    summary = (
        f"{len(top_examples)} exemplo(s) aprovado(s) parecido(s) influenciaram a analise; "
        f"principal sinal historico: {strongest_emotion} (peso {round(strongest_vote, 3)})."
    )
    return {
        "primary_emotion": after_primary,
        "secondary_emotions": secondary,
        "confidence_score": confidence_score,
        "scores_after_learning": scores_after,
        "learning_influence_applied": True,
        "learning_influence_summary": summary,
        "whether_learning_changed_result": changed,
        "learning_adjustments": adjustments,
        "top_learning_examples": top_examples[:3],
    }


def _primary_from_scores(scores: dict) -> str | None:
    candidates = {
        emotion: float(scores.get(emotion, 0.0))
        for emotion in ("urgencia", "inseguranca", "preocupacao", "calma", "ansiedade", "entusiasmo")
    }
    if not candidates:
        return None
    emotion, score = max(candidates.items(), key=lambda item: item[1])
    return emotion if score > 0 else None


def _final_decision_factors(
    *,
    primary_before_learning: str,
    primary_after_learning: str,
    scores_after_learning: dict[str, float],
    learning_influence_summary: str | None,
) -> list[str]:
    factors = [
        f"emocao local antes do aprendizado: {primary_before_learning}",
        f"emocao local apos aprendizado: {primary_after_learning}",
        f"maior score final: {_primary_from_scores(scores_after_learning) or primary_after_learning}",
    ]
    if learning_influence_summary:
        factors.append(learning_influence_summary)
    return factors


def _normalize_label(value: str | None) -> str:
    return _normalize_text(value or "").replace(" ", "_")


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", without_accents).strip()


def _matched_terms(normalized_text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in normalized_text]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _choose_primary_emotion(
    *,
    urgency_score: float,
    uncertainty_score: float,
    concern_score: float,
    calm_score: float,
) -> str:
    if urgency_score >= 0.62:
        return "urgencia"
    if uncertainty_score >= 0.58:
        return "inseguranca"
    if concern_score >= 0.52:
        return "preocupacao"
    if calm_score >= 0.62:
        return "calma"
    return "neutralidade"


def _secondary_emotions(
    *,
    primary_emotion: str,
    urgency_score: float,
    uncertainty_score: float,
    concern_score: float,
    calm_score: float,
) -> list[str]:
    candidates: list[tuple[str, float]] = [
        ("urgencia", urgency_score),
        ("inseguranca", uncertainty_score),
        ("preocupacao", concern_score),
        ("calma", calm_score),
    ]
    emotions = [emotion for emotion, score in sorted(candidates, key=lambda item: item[1], reverse=True) if score >= 0.42]
    return [emotion for emotion in emotions if emotion != primary_emotion][:3] or ["neutralidade"]


def _level(score: float, *, low: str, mid: str, high: str) -> str:
    if score >= 0.67:
        return high
    if score >= 0.38:
        return mid
    return low


def _tone(primary_emotion: str, urgency_score: float, calm_score: float, uncertainty_score: float) -> str:
    if primary_emotion == "urgencia" or urgency_score >= 0.65:
        return "firme e urgente"
    if primary_emotion == "inseguranca" or uncertainty_score >= 0.58:
        return "calmo, pausado e hesitante"
    if primary_emotion == "calma" or calm_score >= 0.62:
        return "calmo e estavel"
    return "controlado, com sinais leves de preocupacao"


def _confidence_score(
    *,
    matched_signal_count: int,
    acoustic_metrics: AcousticMetrics,
    transcription: Transcription,
    settings: Settings,
) -> float:
    base = 0.46
    signal_bonus = min(0.22, matched_signal_count * 0.035)
    audio_bonus = 0.06 if acoustic_metrics.duration_seconds >= 3 else 0.0
    words_bonus = 0.08 if transcription.word_count >= 8 else 0.0
    timeline_bonus = 0.04 if acoustic_metrics.volume_timeline else 0.0
    score = _clamp(base + signal_bonus + audio_bonus + words_bonus + timeline_bonus, 0.35, 0.86)
    return round(max(settings.emotion_confidence_threshold, score), 3)


def _build_evidence(
    *,
    urgency_terms: list[str],
    negative_terms: list[str],
    uncertainty_terms: list[str],
    calm_terms: list[str],
    acoustic_metrics: AcousticMetrics,
    transcription: Transcription,
) -> list[EmotionEvidence]:
    evidence: list[EmotionEvidence] = []
    if urgency_terms:
        evidence.append(
            EmotionEvidence(
                type="text",
                signal="termos de urgencia",
                value=", ".join(urgency_terms),
                impact="aumenta a estimativa de urgencia",
            )
        )
    if negative_terms:
        evidence.append(
            EmotionEvidence(
                type="text",
                signal="termos de dificuldade ou problema",
                value=", ".join(negative_terms),
                impact="aumenta preocupacao ou frustracao leve",
            )
        )
    if uncertainty_terms:
        evidence.append(
            EmotionEvidence(
                type="text",
                signal="marcadores de incerteza",
                value=", ".join(uncertainty_terms),
                impact="sugere duvida, hesitacao ou inseguranca",
            )
        )
    if calm_terms:
        evidence.append(
            EmotionEvidence(
                type="text",
                signal="marcadores de calma",
                value=", ".join(calm_terms),
                impact="aumenta a estimativa de tom calmo",
            )
        )
    evidence.extend(
        [
            EmotionEvidence(
                type="audio",
                signal="silence_ratio",
                value=round(acoustic_metrics.silence_ratio, 3),
                impact="proporcao de pausas ajuda a estimar hesitacao ou controle do ritmo",
            ),
            EmotionEvidence(
                type="audio",
                signal="avg_volume_db",
                value=round(acoustic_metrics.avg_volume_db, 2),
                impact="volume medio ajuda a distinguir fala baixa, estavel ou enfatica",
            ),
            EmotionEvidence(
                type="speech_rate",
                signal="words_per_minute",
                value=round(transcription.words_per_minute, 2),
                impact="ritmo de fala complementa a interpretacao textual",
            ),
        ]
    )
    return evidence


def _observations(
    *,
    primary_emotion: str,
    urgency_level: str,
    calmness_level: str,
    evidence: list[EmotionEvidence],
    learning_examples: list[LearningExampleReference],
) -> list[str]:
    observations = [
        f"Analise emocional interpretativa gerada por fallback local: {primary_emotion}.",
        f"Urgencia estimada como {urgency_level} e calma estimada como {calmness_level}.",
        "A conclusao combina texto transcrito, pausas, volume e ritmo; nenhuma metrica isolada define a emocao.",
    ]
    if learning_examples:
        observations.append(
            f"{len(learning_examples)} exemplo(s) local(is) de aprendizado foram considerados como contexto."
        )
    if evidence:
        observations.append(f"Foram usados {len(evidence)} sinais objetivos/textuais como evidencia.")
    return observations


def _recommended_context(primary_emotion: str, urgency_level: str, calmness_level: str) -> str:
    if primary_emotion == "urgencia":
        return (
            "Responder com objetividade, priorizar passos claros e reconhecer a urgencia sem elevar o tom. "
            "Evitar respostas longas antes de oferecer uma acao concreta."
        )
    if primary_emotion == "inseguranca":
        return (
            "Responder de forma acolhedora e estruturada, validando a duvida e oferecendo proximos passos simples. "
            "Evitar pressupor irritacao."
        )
    if primary_emotion == "calma":
        return (
            "Responder em tom tranquilo e direto. O usuario parece aberto a explicacoes claras e sem pressa."
        )
    return (
        f"Responder com tom claro e cuidadoso. A urgencia parece {urgency_level} e a calma {calmness_level}; "
        "confirmar entendimento antes de inferir estados emocionais fortes."
    )


def _annotate_transcription(
    *,
    transcription: Transcription,
    primary_emotion: str,
    emotional_tone: str,
    evidence: list[EmotionEvidence],
    language: str,
    source: str,
) -> AnnotatedTranscription:
    observation = _annotation_observation(primary_emotion, evidence)
    if transcription.segments:
        annotated_segments = []
        for segment in transcription.segments[:6]:
            segment_emotion = _segment_emotion(segment.text, primary_emotion)
            annotated_segments.append(
                f"{segment.text.strip()} [emoção: {segment_emotion} | tom: {emotional_tone} | observação: {observation}]"
            )
        remaining_segments = transcription.segments[6:]
        if remaining_segments:
            annotated_segments.extend(segment.text.strip() for segment in remaining_segments)
        text = " ".join(item for item in annotated_segments if item)
    else:
        first_sentence = transcription.text.strip() or "Sem fala transcrita"
        text = (
            f"{first_sentence} [emoção: {primary_emotion} | tom: {emotional_tone} | "
            f"observação: {observation}]"
        )

    return AnnotatedTranscription(
        text=text,
        language=language,
        analysis_source=source,
    )


def _annotation_observation(primary_emotion: str, evidence: list[EmotionEvidence]) -> str:
    preferred_signal = {
        "urgencia": "termos de urgencia",
        "inseguranca": "marcadores de incerteza",
        "preocupacao": "termos de dificuldade ou problema",
        "calma": "marcadores de calma",
    }.get(primary_emotion)
    for item in evidence:
        if item.signal == preferred_signal:
            return item.impact
    if evidence:
        return evidence[0].impact
    return "analise baseada em texto e metricas acusticas disponiveis"


def _segment_emotion(text: str, default: str) -> str:
    normalized = _normalize_text(text)
    if any(term in normalized for term in ("agora", "urgente", "nao pode esperar", "rapida")):
        return "urgencia"
    if any(term in normalized for term in ("talvez", "nao tenho certeza", "inseguro")):
        return "inseguranca"
    if any(term in normalized for term in ("problema", "errado", "nao funciona")):
        return "preocupacao"
    if any(term in normalized for term in ("calma", "tranquila", "sem pressa")):
        return "calma"
    return default


def _implicit_emotion(primary_emotion: str, uncertainty_score: float, concern_score: float) -> str:
    if primary_emotion == "urgencia":
        return "necessidade de resposta rapida diante de uma dificuldade percebida"
    if uncertainty_score >= 0.58:
        return "possivel inseguranca ou duvida sobre a propria explicacao"
    if concern_score >= 0.52:
        return "preocupacao com um problema ainda nao resolvido"
    if primary_emotion == "calma":
        return "estado controlado e colaborativo"
    return "estado emocional leve ou neutro com evidencia limitada"


def _calmness_phrase(calmness_level: str) -> str:
    return {
        "alto": "calmo",
        "medio": "moderadamente calmo",
        "baixo": "pouco calmo",
    }.get(calmness_level, "moderadamente calmo")


def _intention(urgency_score: float, uncertainty_score: float, concern_score: float) -> str:
    if urgency_score >= 0.62:
        return "solicitacao tecnica urgente"
    if uncertainty_score >= 0.58:
        return "pedido de ajuda com duvida ou inseguranca"
    if concern_score >= 0.52:
        return "pedido de ajuda tecnica"
    return "explicacao ou teste do sistema"


def _string_list(value: object, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        strings = [str(item) for item in value if str(item).strip()]
        return strings or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _number_or_default(value: object, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    if math.isnan(number) or math.isinf(number):
        return fallback
    return round(_clamp(number), 3)


def _evidence_from_payload(value: object, fallback: list[EmotionEvidence]) -> list[EmotionEvidence]:
    if not isinstance(value, list):
        return fallback
    evidence: list[EmotionEvidence] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        evidence.append(
            EmotionEvidence(
                type=str(item.get("type") or "unknown"),
                signal=str(item.get("signal") or "sinal nao especificado"),
                value=item.get("value"),
                impact=str(item.get("impact") or "impacto nao especificado"),
            )
        )
    return evidence or fallback
