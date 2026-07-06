from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import SQLModel, Session, create_engine

from app.core.config import get_settings

_engine: Engine | None = None
_engine_url: str | None = None


def get_engine() -> Engine:
    global _engine, _engine_url

    settings = get_settings()
    if _engine is None or _engine_url != settings.database_url:
        connect_args = (
            {"check_same_thread": False}
            if settings.database_url.startswith("sqlite")
            else {}
        )
        _engine = create_engine(settings.database_url, connect_args=connect_args)
        _engine_url = settings.database_url
    return _engine


def create_db_and_tables() -> None:
    from app.db import models  # noqa: F401

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _ensure_audio_analysis_columns(engine)
    _ensure_audio_metrics_columns(engine)
    _ensure_feedback_columns(engine)
    _ensure_learning_example_columns(engine)


def _ensure_audio_analysis_columns(engine: Engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "audio_analysis" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("audio_analysis")}
    required_columns = {
        "transcription_segments_json": "TEXT DEFAULT '[]'",
        "transcription_words_json": "TEXT DEFAULT '[]'",
        "transcription_engine": "TEXT",
        "transcription_model": "TEXT",
        "transcription_status": "TEXT DEFAULT 'mocked'",
        "detected_language": "TEXT",
        "word_count": "INTEGER DEFAULT 0",
        "words_per_minute": "REAL DEFAULT 0.0",
        "estimated_speech_rate_label": "TEXT",
        "average_word_duration_ms": "REAL",
        "emotion_status": "TEXT DEFAULT 'mocked'",
        "emotion_analysis_source": "TEXT",
        "emotion_analysis_model": "TEXT",
        "emotion_summary_json": "TEXT DEFAULT '{}'",
        "primary_emotion": "TEXT",
        "secondary_emotions_json": "TEXT DEFAULT '[]'",
        "confidence_score": "REAL DEFAULT 0.0",
        "learning_examples_used_json": "TEXT DEFAULT '[]'",
        "warnings_json": "TEXT DEFAULT '[]'",
        "emotion_debug_json": "TEXT DEFAULT '{}'",
        "emotion_comparison_json": "TEXT DEFAULT '{}'",
        "learning_influence_summary": "TEXT",
        "learning_adjustments_json": "TEXT DEFAULT '[]'",
    }

    with engine.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE audio_analysis ADD COLUMN {column_name} {column_definition}")
                )


def _ensure_audio_metrics_columns(engine: Engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "audio_metrics" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("audio_metrics")}
    required_columns = {
        "duration_seconds": "REAL DEFAULT 0.0",
        "sample_rate": "INTEGER DEFAULT 0",
        "peak_volume_db": "REAL DEFAULT 0.0",
        "dynamic_range_db": "REAL DEFAULT 0.0",
        "silence_count": "INTEGER DEFAULT 0",
        "total_silence_duration_seconds": "REAL DEFAULT 0.0",
        "silence_ratio": "REAL DEFAULT 0.0",
        "longest_silence_seconds": "REAL DEFAULT 0.0",
        "estimated_speech_duration_seconds": "REAL DEFAULT 0.0",
        "peak_count": "INTEGER DEFAULT 0",
        "peak_events_json": "TEXT DEFAULT '[]'",
        "volume_timeline_json": "TEXT DEFAULT '[]'",
        "is_mostly_silent": "BOOLEAN DEFAULT 0",
        "audio_quality_warning": "TEXT",
        "analysis_window_seconds": "REAL DEFAULT 0.5",
    }

    with engine.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE audio_metrics ADD COLUMN {column_name} {column_definition}")
                )
def _ensure_feedback_columns(engine: Engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "emotion_feedback" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("emotion_feedback")}
    required_columns = {
        "corrected_tone": "TEXT",
        "correction_reason": "TEXT",
        "approved_for_learning": "BOOLEAN",
    }

    with engine.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE emotion_feedback ADD COLUMN {column_name} {column_definition}")
                )


def _ensure_learning_example_columns(engine: Engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "learning_examples" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("learning_examples")}
    required_columns = {
        "metrics_snapshot_json": "TEXT DEFAULT '{}'",
        "acoustic_metrics_snapshot_json": "TEXT DEFAULT '{}'",
        "speech_rate_snapshot_json": "TEXT DEFAULT '{}'",
        "transcription_excerpt": "TEXT",
        "emotion_status": "TEXT",
        "emotion_analysis_source": "TEXT",
        "original_primary_emotion": "TEXT",
        "original_secondary_emotions_json": "TEXT DEFAULT '[]'",
        "original_tone": "TEXT",
        "corrected_primary_emotion": "TEXT",
        "corrected_tone": "TEXT",
        "correction_reason": "TEXT",
        "updated_at": "TIMESTAMP",
    }

    with engine.begin() as connection:
        for column_name, column_definition in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE learning_examples ADD COLUMN {column_name} {column_definition}")
                )


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session


def reset_engine_for_tests() -> None:
    global _engine, _engine_url

    if _engine is not None:
        _engine.dispose()
    _engine = None
    _engine_url = None
