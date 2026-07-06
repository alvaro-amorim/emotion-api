import json
import re
import unicodedata
from datetime import datetime, timezone

from sqlmodel import Session, select

from app.api.schemas import (
    AnalysisDebugResponse,
    AnalysisListResponse,
    AudioAnalysisResponse,
    EmotionFeedbackRequest,
    FeedbackResponse,
    LearningContextResponse,
    LearningExampleUpdateRequest,
    LearningExampleReference,
    LearningExampleResponse,
    LearningExamplesListResponse,
)
from app.core.errors import AnalysisNotFoundError
from app.db.models import (
    AudioAnalysis,
    AudioMetrics,
    EmotionFeedback,
    LearningExample,
    WordMetrics,
)
from app.utils.text_utils import text_excerpt


def _response_from_payload(payload: dict) -> AudioAnalysisResponse:
    metadata = payload.setdefault("metadata", {})
    if "audio_duration_seconds" not in metadata:
        metadata["audio_duration_seconds"] = metadata.get("duration_seconds", 0.0)

    payload.setdefault(
        "status",
        {
            "acoustic_metrics_status": "real",
            "transcription_status": "mocked",
            "emotion_status": "mocked",
            "emotion_analysis_source": None,
        },
    )
    payload.setdefault("emotion_evidence", [])
    payload.setdefault("emotion_debug", {})
    payload.setdefault("emotion_comparison", {})
    payload.setdefault("learning_examples_used", [])
    payload.setdefault("learning_influence_summary", None)
    payload.setdefault("whether_learning_changed_result", False)
    payload.setdefault("learning_adjustments", [])

    transcription = payload.setdefault("transcription", {})
    transcription.setdefault("transcription_engine", "mock")
    transcription.setdefault("transcription_model", "mock")
    transcription.setdefault("detected_language", metadata.get("language", "pt-BR"))
    transcription.setdefault("word_count", len((transcription.get("text") or "").split()))
    transcription.setdefault("words_per_minute", 0.0)
    transcription.setdefault("estimated_speech_rate_label", "normal")
    transcription.setdefault("average_word_duration_ms", None)

    annotated = payload.setdefault("annotated_transcription", {})
    annotated.setdefault("analysis_source", payload["status"].get("emotion_analysis_source"))

    emotion_summary = payload.setdefault("emotion_summary", {})
    emotion_summary.setdefault("emotional_tone", None)
    emotion_summary.setdefault("calmness_level", None)
    emotion_summary.setdefault("calmness_score", None)
    emotion_summary.setdefault("tension_score", None)
    emotion_summary.setdefault("interpretation_summary", None)
    emotion_summary.setdefault("analysis_source", payload["status"].get("emotion_analysis_source"))
    emotion_summary.setdefault("analysis_model", None)
    emotion_summary.setdefault("analysis_status", payload["status"].get("emotion_status"))

    emotion_debug = payload.setdefault("emotion_debug", {})
    emotion_debug.setdefault("provider_requested", "unknown")
    emotion_debug.setdefault("cohere_enabled", False)
    emotion_debug.setdefault("cohere_attempted", False)
    emotion_debug.setdefault("cohere_success", False)
    emotion_debug.setdefault("fallback_used", payload["status"].get("emotion_status") != "real")
    emotion_debug.setdefault("fallback_reason", None)
    emotion_debug.setdefault("local_fallback_result", {})
    emotion_debug.setdefault("cohere_result_raw_excerpt", None)
    emotion_debug.setdefault("learning_examples_count", len(payload.get("learning_examples_used", [])))
    emotion_debug.setdefault("learning_examples_requested", False)
    emotion_debug.setdefault("learning_examples_found", emotion_debug.get("learning_examples_count", 0))
    emotion_debug.setdefault("learning_examples_used_count", len(payload.get("learning_examples_used", [])))
    emotion_debug.setdefault("learning_min_similarity", None)
    emotion_debug.setdefault("top_learning_examples", [])
    emotion_debug.setdefault("learning_influence_applied", False)
    emotion_debug.setdefault("learning_influence_summary", payload.get("learning_influence_summary"))
    emotion_debug.setdefault("whether_learning_changed_result", payload.get("whether_learning_changed_result", False))
    emotion_debug.setdefault("learning_adjustments", payload.get("learning_adjustments", []))
    emotion_debug.setdefault("heuristic_weights_snapshot", {})
    emotion_debug.setdefault("heuristic_scores", {})
    emotion_debug.setdefault("final_decision_factors", [])
    emotion_debug.setdefault("warnings", payload.get("quality_warnings", []))

    emotion_comparison = payload.setdefault("emotion_comparison", {})
    emotion_comparison.setdefault("local_before_learning", emotion_summary.get("primary_emotion"))
    emotion_comparison.setdefault("local_after_learning", emotion_summary.get("primary_emotion"))
    emotion_comparison.setdefault("local_primary_emotion", emotion_summary.get("primary_emotion"))
    emotion_comparison.setdefault(
        "cohere_primary_emotion",
        emotion_summary.get("primary_emotion") if payload["status"].get("emotion_analysis_source") == "cohere" else None,
    )
    emotion_comparison.setdefault("cohere_result", emotion_comparison.get("cohere_primary_emotion"))
    emotion_comparison.setdefault(
        "agreement_level",
        "full" if payload["status"].get("emotion_analysis_source") == "cohere" else "local_only",
    )
    emotion_comparison.setdefault(
        "learning_changed_local_result",
        payload.get("whether_learning_changed_result", False),
    )
    emotion_comparison.setdefault("differences", [])

    if "acoustic_metrics" not in payload:
        prosody = payload.get("prosody_summary", {})
        duration = metadata.get("duration_seconds", 0.0)
        payload["acoustic_metrics"] = {
            "duration_seconds": duration,
            "sample_rate": 0,
            "avg_volume_db": prosody.get("avg_volume_db", 0.0),
            "peak_volume_db": prosody.get("max_volume_db", 0.0),
            "volume_variance": prosody.get("volume_variance", 0.0),
            "dynamic_range_db": 0.0,
            "silence_count": 0,
            "total_silence_duration_seconds": 0.0,
            "silence_ratio": prosody.get("pause_ratio", 0.0),
            "longest_silence_seconds": 0.0,
            "estimated_speech_duration_seconds": duration,
            "peak_count": 0,
            "peak_events": [],
            "volume_timeline": [],
            "is_mostly_silent": False,
            "audio_quality_warning": "Métricas antigas sem cálculo acústico detalhado.",
            "analysis_window_seconds": 0.5,
        }

    return AudioAnalysisResponse.model_validate(payload)


def create_audio_analysis(
    session: Session,
    response: AudioAnalysisResponse,
) -> AudioAnalysisResponse:
    payload = response.model_dump(mode="json")
    payload_json = json.dumps(payload, ensure_ascii=False)

    analysis = AudioAnalysis(
        id=response.analysis_id,
        file_name=response.metadata.file_name,
        file_hash=response.metadata.file_hash,
        duration_seconds=response.metadata.duration_seconds,
        language=response.metadata.language,
        transcription_text=response.transcription.text,
        transcription_segments_json=json.dumps(
            [item.model_dump(mode="json") for item in response.transcription.segments],
            ensure_ascii=False,
        ),
        transcription_words_json=json.dumps(
            [item.model_dump(mode="json") for item in response.transcription.words],
            ensure_ascii=False,
        ),
        transcription_engine=response.transcription.transcription_engine,
        transcription_model=response.transcription.transcription_model,
        transcription_status=response.status.transcription_status,
        detected_language=response.transcription.detected_language,
        word_count=response.transcription.word_count,
        words_per_minute=response.transcription.words_per_minute,
        estimated_speech_rate_label=response.transcription.estimated_speech_rate_label,
        average_word_duration_ms=response.transcription.average_word_duration_ms,
        annotated_transcription=response.annotated_transcription.text,
        final_summary_json=payload_json,
        emotion_status=response.status.emotion_status,
        emotion_analysis_source=response.status.emotion_analysis_source,
        emotion_analysis_model=response.emotion_summary.analysis_model,
        emotion_summary_json=json.dumps(response.emotion_summary.model_dump(mode="json"), ensure_ascii=False),
        primary_emotion=response.emotion_summary.primary_emotion,
        secondary_emotions_json=json.dumps(response.emotion_summary.secondary_emotions, ensure_ascii=False),
        confidence_score=response.emotion_summary.confidence_score,
        learning_examples_used_json=json.dumps(
            [item.model_dump(mode="json") for item in response.learning_examples_used],
            ensure_ascii=False,
        ),
        warnings_json=json.dumps(response.quality_warnings, ensure_ascii=False),
        emotion_debug_json=json.dumps(response.emotion_debug.model_dump(mode="json"), ensure_ascii=False),
        emotion_comparison_json=json.dumps(response.emotion_comparison.model_dump(mode="json"), ensure_ascii=False),
        learning_influence_summary=response.learning_influence_summary,
        learning_adjustments_json=json.dumps(response.learning_adjustments, ensure_ascii=False),
        recommended_context_for_ai_agent=response.recommended_context_for_ai_agent,
        external_ai_used=response.metadata.external_ai_used,
        processing_version=response.metadata.processing_version,
        created_at=response.metadata.created_at,
    )
    session.add(analysis)

    metrics = AudioMetrics(
        analysis_id=response.analysis_id,
        duration_seconds=response.acoustic_metrics.duration_seconds,
        sample_rate=response.acoustic_metrics.sample_rate,
        avg_volume_db=response.acoustic_metrics.avg_volume_db,
        max_volume_db=response.acoustic_metrics.peak_volume_db,
        peak_volume_db=response.acoustic_metrics.peak_volume_db,
        volume_variance=response.acoustic_metrics.volume_variance,
        dynamic_range_db=response.acoustic_metrics.dynamic_range_db,
        silence_count=response.acoustic_metrics.silence_count,
        total_silence_duration_seconds=response.acoustic_metrics.total_silence_duration_seconds,
        silence_ratio=response.acoustic_metrics.silence_ratio,
        longest_silence_seconds=response.acoustic_metrics.longest_silence_seconds,
        estimated_speech_duration_seconds=response.acoustic_metrics.estimated_speech_duration_seconds,
        peak_count=response.acoustic_metrics.peak_count,
        peak_events_json=json.dumps(
            [item.model_dump(mode="json") for item in response.acoustic_metrics.peak_events],
            ensure_ascii=False,
        ),
        volume_timeline_json=json.dumps(
            [item.model_dump(mode="json") for item in response.acoustic_metrics.volume_timeline],
            ensure_ascii=False,
        ),
        is_mostly_silent=response.acoustic_metrics.is_mostly_silent,
        audio_quality_warning=response.acoustic_metrics.audio_quality_warning,
        analysis_window_seconds=response.acoustic_metrics.analysis_window_seconds,
        speech_rate_wpm=response.prosody_summary.speech_rate_wpm,
        pause_ratio=response.acoustic_metrics.silence_ratio,
        calmness_score=response.prosody_summary.calmness_score,
        tension_score=response.prosody_summary.tension_score,
    )
    session.add(metrics)

    emphasis_by_word = {
        item.word.lower(): item.emphasis_score for item in response.prosody_summary.emphasis_words
    }
    for word in response.transcription.words:
        session.add(
            WordMetrics(
                analysis_id=response.analysis_id,
                word=word.word,
                start_time=word.start,
                end_time=word.end,
                duration_ms=word.duration_ms,
                pause_before_ms=word.pause_before_ms,
                pause_after_ms=word.pause_after_ms,
                volume_at_word=response.prosody_summary.avg_volume_db,
                emphasis_score=emphasis_by_word.get(word.word.lower(), 0.0),
                confidence=word.confidence or 0.0,
            )
        )

    session.commit()
    return response


def get_audio_analysis_response(session: Session, analysis_id: str) -> AudioAnalysisResponse:
    analysis = session.get(AudioAnalysis, analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError(analysis_id)
    return _response_from_payload(json.loads(analysis.final_summary_json))


def get_analysis_debug_response(session: Session, analysis_id: str) -> AnalysisDebugResponse:
    analysis = session.get(AudioAnalysis, analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError(analysis_id)
    response = _response_from_payload(json.loads(analysis.final_summary_json))
    return AnalysisDebugResponse(
        analysis_id=analysis_id,
        status=response.status,
        emotion_debug=response.emotion_debug,
        emotion_comparison=response.emotion_comparison,
    )


def list_audio_analysis_responses(
    session: Session,
    *,
    limit: int,
    offset: int,
) -> AnalysisListResponse:
    statement = (
        select(AudioAnalysis)
        .order_by(AudioAnalysis.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = session.exec(statement).all()
    analyses = [_response_from_payload(json.loads(row.final_summary_json)) for row in rows]
    return AnalysisListResponse(
        analyses=analyses,
        limit=limit,
        offset=offset,
        count=len(analyses),
    )


def count_audio_analyses(session: Session) -> int:
    return len(session.exec(select(AudioAnalysis.id)).all())


def count_learning_examples(session: Session) -> int:
    return len(session.exec(select(LearningExample.id)).all())


def save_feedback(
    session: Session,
    analysis_id: str,
    payload: EmotionFeedbackRequest,
) -> FeedbackResponse:
    analysis = session.get(AudioAnalysis, analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError(analysis_id)

    feedback = EmotionFeedback(
        analysis_id=analysis_id,
        rating=payload.rating,
        is_correct=payload.is_correct,
        corrected_primary_emotion=payload.corrected_primary_emotion,
        corrected_secondary_emotions=json.dumps(
            payload.corrected_secondary_emotions,
            ensure_ascii=False,
        )
        if payload.corrected_secondary_emotions is not None
        else None,
        corrected_intention=payload.corrected_intention,
        corrected_tone=payload.corrected_tone,
        correction_reason=payload.correction_reason,
        approved_for_learning=payload.approved_for_learning,
        notes=payload.notes,
    )
    session.add(feedback)
    session.flush()

    response_payload = json.loads(analysis.final_summary_json)
    original_prediction = response_payload.get("emotion_summary", {})
    original_secondary = original_prediction.get("secondary_emotions") or []
    corrected_primary = payload.corrected_primary_emotion or (
        original_prediction.get("primary_emotion") if payload.is_correct else None
    )
    corrected_tone = payload.corrected_tone or (
        original_prediction.get("emotional_tone") if payload.is_correct else None
    )
    corrected_prediction = {
        "primary_emotion": corrected_primary,
        "secondary_emotions": payload.corrected_secondary_emotions or (original_secondary if payload.is_correct else []),
        "intention": payload.corrected_intention or (original_prediction.get("intention") if payload.is_correct else None),
        "tone": corrected_tone,
        "correction_reason": payload.correction_reason,
        "is_correct": payload.is_correct,
        "rating": payload.rating,
    }
    should_create_example = (
        payload.is_correct
        or payload.rating == "positive"
        or bool(payload.corrected_primary_emotion)
        or bool(payload.corrected_intention)
    )

    if should_create_example:
        approved_for_reuse = (
            payload.approved_for_learning
            if payload.approved_for_learning is not None
            else payload.is_correct or payload.rating == "positive"
        )
        acoustic_snapshot = response_payload.get("acoustic_metrics", {})
        speech_snapshot = {
            "word_count": response_payload.get("transcription", {}).get("word_count"),
            "words_per_minute": response_payload.get("transcription", {}).get("words_per_minute"),
            "estimated_speech_rate_label": response_payload.get("transcription", {}).get(
                "estimated_speech_rate_label"
            ),
        }
        metrics_snapshot = {
            "acoustic_metrics": acoustic_snapshot,
            "prosody_summary": response_payload.get("prosody_summary", {}),
            "transcription": speech_snapshot,
        }
        existing_example = session.exec(
            select(LearningExample).where(LearningExample.source_analysis_id == analysis_id)
        ).first()
        example = existing_example or LearningExample(
            source_analysis_id=analysis_id,
            text_excerpt=text_excerpt(analysis.transcription_text),
            original_prediction=json.dumps(original_prediction, ensure_ascii=False),
            corrected_prediction=json.dumps(corrected_prediction, ensure_ascii=False),
        )
        example.text_excerpt = text_excerpt(analysis.transcription_text)
        example.original_prediction = json.dumps(original_prediction, ensure_ascii=False)
        example.corrected_prediction = json.dumps(corrected_prediction, ensure_ascii=False)
        example.metrics_snapshot_json = json.dumps(metrics_snapshot, ensure_ascii=False)
        example.acoustic_metrics_snapshot_json = json.dumps(acoustic_snapshot, ensure_ascii=False)
        example.speech_rate_snapshot_json = json.dumps(speech_snapshot, ensure_ascii=False)
        example.transcription_excerpt = text_excerpt(analysis.transcription_text, limit=600)
        example.emotion_status = analysis.emotion_status
        example.emotion_analysis_source = analysis.emotion_analysis_source
        example.original_primary_emotion = original_prediction.get("primary_emotion")
        example.original_secondary_emotions_json = json.dumps(original_secondary, ensure_ascii=False)
        example.original_tone = original_prediction.get("emotional_tone")
        example.corrected_primary_emotion = corrected_primary
        example.corrected_tone = corrected_tone
        example.correction_reason = payload.correction_reason
        example.user_notes = payload.notes
        example.approved_for_reuse = approved_for_reuse
        example.updated_at = datetime.now(timezone.utc)
        session.add(example)

    session.commit()
    session.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id or 0,
        analysis_id=analysis_id,
        rating=payload.rating,
        is_correct=payload.is_correct,
        learning_example_created=should_create_example,
        message="Feedback registrado com sucesso.",
        created_at=feedback.created_at,
    )


def list_learning_examples(
    session: Session,
    *,
    approved_only: bool | None = None,
    limit: int = 100,
    corrected_emotion: str | None = None,
    source_analysis_id: str | None = None,
) -> LearningExamplesListResponse:
    statement = select(LearningExample).order_by(LearningExample.created_at.desc())
    if approved_only is not None:
        statement = statement.where(LearningExample.approved_for_reuse == approved_only)
    if corrected_emotion:
        statement = statement.where(LearningExample.corrected_primary_emotion == corrected_emotion)
    if source_analysis_id:
        statement = statement.where(LearningExample.source_analysis_id == source_analysis_id)
    statement = statement.limit(limit)
    rows = session.exec(statement).all()
    examples = [
        _learning_example_response(row)
        for row in rows
    ]
    return LearningExamplesListResponse(examples=examples, count=len(examples))


def update_learning_example(
    session: Session,
    example_id: int,
    payload: LearningExampleUpdateRequest,
) -> LearningExampleResponse | None:
    row = session.get(LearningExample, example_id)
    if row is None:
        return None

    fields = payload.model_dump(exclude_unset=True)
    if "approved_for_reuse" in fields:
        row.approved_for_reuse = bool(fields["approved_for_reuse"])
    if "user_notes" in fields:
        row.user_notes = fields["user_notes"]
    if "corrected_primary_emotion" in fields:
        row.corrected_primary_emotion = fields["corrected_primary_emotion"]
    if "corrected_tone" in fields:
        row.corrected_tone = fields["corrected_tone"]
    if "correction_reason" in fields:
        row.correction_reason = fields["correction_reason"]

    corrected_prediction = json.loads(row.corrected_prediction or "{}")
    if "corrected_primary_emotion" in fields:
        corrected_prediction["primary_emotion"] = fields["corrected_primary_emotion"]
    if "corrected_tone" in fields:
        corrected_prediction["tone"] = fields["corrected_tone"]
    if "correction_reason" in fields:
        corrected_prediction["correction_reason"] = fields["correction_reason"]
    row.corrected_prediction = json.dumps(corrected_prediction, ensure_ascii=False)
    row.updated_at = datetime.now(timezone.utc)

    session.add(row)
    session.commit()
    session.refresh(row)
    return _learning_example_response(row)


def _learning_example_response(row: LearningExample) -> LearningExampleResponse:
    original_prediction = json.loads(row.original_prediction)
    corrected_prediction = json.loads(row.corrected_prediction)
    metrics_snapshot = json.loads(row.metrics_snapshot_json or "{}")
    acoustic_snapshot = json.loads(row.acoustic_metrics_snapshot_json or "{}")
    speech_snapshot = json.loads(row.speech_rate_snapshot_json or "{}")
    return LearningExampleResponse(
        id=row.id or 0,
        source_analysis_id=row.source_analysis_id,
        text_excerpt=row.text_excerpt,
        original_prediction=original_prediction,
        corrected_prediction=corrected_prediction,
        original_primary_emotion=row.original_primary_emotion or original_prediction.get("primary_emotion"),
        original_secondary_emotions=json.loads(row.original_secondary_emotions_json or "[]"),
        original_tone=row.original_tone or original_prediction.get("emotional_tone"),
        corrected_primary_emotion=row.corrected_primary_emotion or corrected_prediction.get("primary_emotion"),
        corrected_tone=row.corrected_tone or corrected_prediction.get("tone"),
        correction_reason=row.correction_reason or corrected_prediction.get("correction_reason"),
        metrics_snapshot=metrics_snapshot,
        acoustic_metrics_snapshot=acoustic_snapshot or metrics_snapshot.get("acoustic_metrics", {}),
        speech_rate_snapshot=speech_snapshot or metrics_snapshot.get("transcription", {}),
        transcription_excerpt=row.transcription_excerpt or row.text_excerpt,
        emotion_status=row.emotion_status,
        emotion_analysis_source=row.emotion_analysis_source,
        user_notes=row.user_notes,
        approved_for_reuse=row.approved_for_reuse,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def find_similar_learning_examples(
    session: Session,
    *,
    text: str,
    acoustic_metrics: dict | None = None,
    speech_metrics: dict | None = None,
    limit: int,
    min_similarity: float = 0.20,
    include_unapproved: bool = False,
) -> list[LearningExampleReference]:
    if limit <= 0:
        return []

    acoustic_metrics = acoustic_metrics or {}
    speech_metrics = speech_metrics or {}
    query_tokens = _token_set(text)
    statement = select(LearningExample).order_by(LearningExample.created_at.desc()).limit(80)
    if not include_unapproved:
        statement = statement.where(LearningExample.approved_for_reuse == True)  # noqa: E712
    rows = session.exec(statement).all()

    scored: list[tuple[float, LearningExample, dict]] = []
    for row in rows:
        example_tokens = _token_set(row.text_excerpt)
        matched_terms = sorted(query_tokens & example_tokens)
        if not query_tokens or not example_tokens:
            text_similarity = 0.0
        else:
            text_similarity = len(query_tokens & example_tokens) / len(query_tokens | example_tokens)

        metric_similarity = _metric_similarity(
            acoustic_metrics=acoustic_metrics,
            speech_metrics=speech_metrics,
            row=row,
        )
        recency_score = _recency_score(row.created_at)
        approval_score = 1.0 if row.approved_for_reuse else 0.15
        correction_score = _correction_quality_score(row)
        score = (
            0.42 * text_similarity
            + 0.28 * metric_similarity
            + 0.12 * recency_score
            + 0.12 * approval_score
            + 0.06 * correction_score
        )
        details = {
            "matched_terms": matched_terms[:12],
            "text_similarity": round(text_similarity, 3),
            "metric_similarity": round(metric_similarity, 3),
            "recency_score": round(recency_score, 3),
            "correction_score": round(correction_score, 3),
        }
        scored.append((score, row, details))

    scored.sort(key=lambda item: (item[0], item[1].approved_for_reuse, item[1].created_at), reverse=True)
    selected = [item for item in scored if item[0] >= min_similarity][:limit]
    if not selected and include_unapproved:
        selected = scored[:limit]

    return [
        LearningExampleReference(
            id=row.id or 0,
            source_analysis_id=row.source_analysis_id,
            text_excerpt=row.text_excerpt,
            corrected_prediction=json.loads(row.corrected_prediction),
            similarity_score=round(score, 3),
            matched_terms=details["matched_terms"],
            metric_similarity=details["metric_similarity"],
            text_similarity=details["text_similarity"],
            recency_score=details["recency_score"],
            correction_summary=_correction_summary(row),
            reason_used=_reason_used(details),
            approved_for_reuse=row.approved_for_reuse,
            corrected_primary_emotion=row.corrected_primary_emotion,
            corrected_tone=row.corrected_tone,
        )
        for score, row, details in selected
    ]


def get_learning_context_for_analysis(
    session: Session,
    *,
    analysis_id: str,
    limit: int,
    min_similarity: float,
) -> LearningContextResponse:
    analysis = session.get(AudioAnalysis, analysis_id)
    if analysis is None:
        raise AnalysisNotFoundError(analysis_id)
    response = _response_from_payload(json.loads(analysis.final_summary_json))
    examples = find_similar_learning_examples(
        session,
        text=response.transcription.text,
        acoustic_metrics=response.acoustic_metrics.model_dump(mode="json"),
        speech_metrics={
            "word_count": response.transcription.word_count,
            "words_per_minute": response.transcription.words_per_minute,
            "estimated_speech_rate_label": response.transcription.estimated_speech_rate_label,
        },
        limit=limit,
        min_similarity=min_similarity,
    )
    return LearningContextResponse(
        analysis_id=analysis_id,
        examples=examples,
        count=len(examples),
    )


def _token_set(text: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", text.lower())
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    tokens = set(re.findall(r"[a-z0-9]{3,}", without_accents))
    stopwords = {
        "que",
        "com",
        "para",
        "uma",
        "por",
        "isso",
        "mais",
        "muito",
        "quando",
        "agora",
    }
    return tokens - stopwords


def _metric_similarity(
    *,
    acoustic_metrics: dict,
    speech_metrics: dict,
    row: LearningExample,
) -> float:
    snapshot = json.loads(row.metrics_snapshot_json or "{}")
    acoustic_snapshot = json.loads(row.acoustic_metrics_snapshot_json or "{}") or snapshot.get("acoustic_metrics", {})
    speech_snapshot = json.loads(row.speech_rate_snapshot_json or "{}") or snapshot.get("transcription", {})

    scores = [
        _proximity(acoustic_metrics.get("silence_ratio"), acoustic_snapshot.get("silence_ratio"), scale=0.45),
        _proximity(acoustic_metrics.get("avg_volume_db"), acoustic_snapshot.get("avg_volume_db"), scale=18.0),
        _proximity(acoustic_metrics.get("peak_volume_db"), acoustic_snapshot.get("peak_volume_db"), scale=18.0),
        _proximity(speech_metrics.get("words_per_minute"), speech_snapshot.get("words_per_minute"), scale=90.0),
    ]
    usable = [score for score in scores if score is not None]
    if not usable:
        return 0.0
    return sum(usable) / len(usable)


def _proximity(left: object, right: object, *, scale: float) -> float | None:
    try:
        left_value = float(left)
        right_value = float(right)
    except (TypeError, ValueError):
        return None
    return max(0.0, 1.0 - min(abs(left_value - right_value) / scale, 1.0))


def _recency_score(created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    created = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    age_days = max((now - created).total_seconds() / 86400, 0.0)
    return 1.0 / (1.0 + age_days / 30.0)


def _correction_quality_score(row: LearningExample) -> float:
    score = 0.45
    if row.corrected_primary_emotion:
        score += 0.20
    if row.corrected_tone:
        score += 0.12
    if row.correction_reason:
        score += 0.13
    if row.user_notes:
        score += 0.10
    return min(score, 1.0)


def _correction_summary(row: LearningExample) -> str:
    emotion = row.corrected_primary_emotion or "sem emocao corrigida"
    tone = row.corrected_tone or "sem tom corrigido"
    reason = row.correction_reason or row.user_notes or "sem motivo detalhado"
    return f"correcao: {emotion}; tom: {tone}; motivo: {text_excerpt(reason, limit=160)}"


def _reason_used(details: dict) -> str:
    parts = [
        f"texto={details['text_similarity']}",
        f"metricas={details['metric_similarity']}",
        f"recencia={details['recency_score']}",
    ]
    if details["matched_terms"]:
        parts.append(f"termos={', '.join(details['matched_terms'][:5])}")
    return "; ".join(parts)
