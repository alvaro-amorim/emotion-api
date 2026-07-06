from tests.conftest import create_mock_analysis


def test_analyze_audio_returns_real_acoustics_and_real_transcription_contract(client):
    payload = create_mock_analysis(client)

    assert payload["analysis_id"]
    assert payload["metadata"]["file_name"] == "audio_teste.wav"
    assert payload["metadata"]["language"] == "pt-BR"
    assert payload["metadata"]["processing_version"] == "0.5.0"
    assert payload["metadata"]["external_ai_used"] is False
    assert payload["status"]["acoustic_metrics_status"] == "real"
    assert payload["status"]["transcription_status"] == "real"
    assert payload["status"]["emotion_status"] == "fallback_local"
    assert payload["status"]["emotion_analysis_source"] == "local_heuristics"
    assert payload["acoustic_metrics"]["duration_seconds"] > 0
    assert payload["acoustic_metrics"]["sample_rate"] == 16000
    assert payload["transcription"]["text"]
    assert payload["transcription"]["segments"]
    assert payload["transcription"]["words"]
    assert payload["transcription"]["transcription_engine"] == "faster-whisper"
    assert payload["transcription"]["transcription_model"] == "tiny"
    assert payload["transcription"]["word_count"] > 0
    assert payload["transcription"]["words_per_minute"] > 0
    assert payload["transcription"]["estimated_speech_rate_label"] in {"slow", "normal", "fast"}
    assert "[emoção:" in payload["annotated_transcription"]["text"]
    assert payload["prosody_summary"]["emphasis_words"]
    assert payload["emotion_summary"]["primary_emotion"] != "mocked"
    assert payload["emotion_summary"]["analysis_source"] == "local_heuristics"
    assert payload["emotion_evidence"]
    assert payload["emotion_debug"]["fallback_used"] is True
    assert payload["emotion_debug"]["fallback_reason"] == "use_external_ai=false"
    assert payload["emotion_debug"]["cohere_attempted"] is False
    assert payload["emotion_comparison"]["agreement_level"] == "local_only"
    assert payload["emotion_comparison"]["local_primary_emotion"] == payload["emotion_summary"]["primary_emotion"]
    assert payload["status"]["emotion_status"] != "mocked"
    assert "mock" not in payload["annotated_transcription"]["text"].lower()
    assert payload["feedback"]["feedback_url"].endswith("/feedback")


def test_saved_analysis_can_be_fetched_and_listed(client):
    payload = create_mock_analysis(client)
    analysis_id = payload["analysis_id"]

    fetched = client.get(f"/v1/analyses/{analysis_id}")
    debug = client.get(f"/v1/analyses/{analysis_id}/debug")
    listed = client.get("/v1/analyses")

    assert fetched.status_code == 200
    assert fetched.json()["analysis_id"] == analysis_id
    assert fetched.json()["status"]["transcription_status"] == "real"
    assert debug.status_code == 200
    assert debug.json()["analysis_id"] == analysis_id
    assert debug.json()["emotion_debug"]["fallback_used"] is True
    assert debug.json()["emotion_comparison"]["agreement_level"] == "local_only"
    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert listed.json()["analyses"][0]["analysis_id"] == analysis_id

