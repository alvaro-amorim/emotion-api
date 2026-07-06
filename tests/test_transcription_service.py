from types import SimpleNamespace

from app.services.transcription_service import build_transcription_from_segments


def test_build_transcription_from_segments_normalizes_words_and_speech_rate():
    segments = [
        SimpleNamespace(
            id=0,
            start=0.0,
            end=1.2,
            text="Olá mundo",
            avg_logprob=-0.2,
            words=[
                SimpleNamespace(word="Olá", start=0.0, end=0.35, probability=0.92),
                SimpleNamespace(word="mundo", start=0.55, end=1.0, probability=0.88),
            ],
        )
    ]

    transcription = build_transcription_from_segments(
        segments,
        audio_duration_seconds=2.0,
        transcription_engine="faster-whisper",
        transcription_model="tiny",
        detected_language="pt",
    )

    assert transcription.text == "Olá mundo"
    assert transcription.segments[0].confidence is not None
    assert transcription.words[0].word == "Olá"
    assert transcription.words[0].pause_after_ms == 200
    assert transcription.words[1].pause_before_ms == 200
    assert transcription.word_count == 2
    assert transcription.words_per_minute == 60.0
    assert transcription.estimated_speech_rate_label == "slow"
    assert transcription.average_word_duration_ms == 400.0
