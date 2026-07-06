def test_health_returns_safe_diagnostic_payload(client):
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["app"] == "Audio Emotion API"
    assert payload["version"].startswith("0.5.")
    assert payload["environment"]
    assert payload["python_version"]
    assert payload["transcription_engine"] == "faster-whisper"
    assert payload["whisper_model_size"] == "tiny"
    assert payload["emotion_provider"] == "hybrid"
    assert payload["cohere_enabled"] is False
    assert payload["database_url"].startswith("sqlite:///")
    assert "COHERE_API_KEY" not in response.text
    assert "fake-key" not in response.text
