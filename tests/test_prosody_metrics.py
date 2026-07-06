from tests.conftest import make_wav_bytes


def test_real_acoustic_metrics_have_expected_shape(client):
    response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "tone_with_pause.wav",
                make_wav_bytes(
                    duration_seconds=2.0,
                    amplitude=0.45,
                    silence_ranges=[(0.75, 1.25)],
                ),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    metrics = payload["acoustic_metrics"]
    prosody = payload["prosody_summary"]

    assert payload["status"]["acoustic_metrics_status"] == "real"
    assert payload["status"]["transcription_status"] == "real"
    assert payload["status"]["emotion_status"] == "fallback_local"
    assert abs(metrics["duration_seconds"] - 2.0) < 0.08
    assert metrics["sample_rate"] == 16000
    assert metrics["avg_volume_db"] < 0
    assert metrics["peak_volume_db"] < 0
    assert metrics["silence_count"] >= 1
    assert metrics["total_silence_duration_seconds"] >= 0.45
    assert metrics["silence_ratio"] > 0.1
    assert metrics["estimated_speech_duration_seconds"] < metrics["duration_seconds"]
    assert isinstance(metrics["peak_events"], list)
    assert prosody["avg_volume_db"] == metrics["avg_volume_db"]
    assert prosody["max_volume_db"] == metrics["peak_volume_db"]


def test_real_acoustic_metrics_are_saved_in_database(client):
    from sqlmodel import Session, select

    from app.db.models import AudioAnalysis, AudioMetrics
    from app.db.session import get_engine

    response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "persisted.wav",
                make_wav_bytes(duration_seconds=1.2, amplitude=0.25),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 201, response.text
    analysis_id = response.json()["analysis_id"]

    with Session(get_engine()) as session:
        metrics = session.exec(
            select(AudioMetrics).where(AudioMetrics.analysis_id == analysis_id)
        ).one()
        analysis = session.get(AudioAnalysis, analysis_id)

    assert abs(metrics.duration_seconds - 1.2) < 0.08
    assert metrics.sample_rate == 16000
    assert metrics.peak_volume_db < 0
    assert metrics.volume_timeline_json != "[]"
    assert analysis is not None
    assert analysis.transcription_text == "Eu preciso resolver este problema agora, mas estou falando com calma."
    assert analysis.transcription_status == "real"
    assert analysis.transcription_engine == "faster-whisper"
    assert analysis.transcription_model == "tiny"
    assert analysis.transcription_segments_json != "[]"
    assert analysis.emotion_status == "fallback_local"
    assert analysis.emotion_analysis_source == "local_heuristics"
    assert analysis.emotion_summary_json != "{}"
    assert analysis.primary_emotion
    assert analysis.confidence_score > 0


def test_silent_audio_generates_high_silence_ratio(client):
    response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "silent.wav",
                make_wav_bytes(duration_seconds=1.0, amplitude=0.0),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 201, response.text
    metrics = response.json()["acoustic_metrics"]

    assert metrics["silence_ratio"] >= 0.9
    assert metrics["is_mostly_silent"] is True
    assert metrics["audio_quality_warning"]


def test_quieter_audio_has_lower_average_volume(client):
    loud_response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "loud.wav",
                make_wav_bytes(duration_seconds=0.8, amplitude=0.6),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )
    quiet_response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "quiet.wav",
                make_wav_bytes(duration_seconds=0.8, amplitude=0.08),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert loud_response.status_code == 201, loud_response.text
    assert quiet_response.status_code == 201, quiet_response.text

    loud_volume = loud_response.json()["acoustic_metrics"]["avg_volume_db"]
    quiet_volume = quiet_response.json()["acoustic_metrics"]["avg_volume_db"]

    assert quiet_volume < loud_volume
