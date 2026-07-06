from app.core.config import get_settings
from tests.conftest import make_wav_bytes


def _enable_api_key(monkeypatch, *, key: str = "test-local-key") -> None:
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    monkeypatch.setenv("LOCAL_API_KEY", key)
    monkeypatch.setenv("API_KEY_HEADER_NAME", "X-API-Key")
    get_settings.cache_clear()


def _post_audio(client, *, headers: dict | None = None):
    return client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "audio_teste.wav",
                make_wav_bytes(duration_seconds=0.8, amplitude=0.3),
                "audio/wav",
            )
        },
        data={
            "language": "pt-BR",
            "use_external_ai": "false",
            "interpretation_style": "interpretative",
        },
        headers=headers or {},
    )


def test_analyze_audio_works_without_api_key_when_disabled(client):
    response = _post_audio(client)

    assert response.status_code == 201
    assert response.json()["analysis_id"]


def test_analyze_audio_returns_401_without_api_key_when_required(client, monkeypatch):
    _enable_api_key(monkeypatch)

    response = _post_audio(client)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_analyze_audio_returns_401_with_wrong_api_key(client, monkeypatch):
    _enable_api_key(monkeypatch)

    response = _post_audio(client, headers={"X-API-Key": "wrong-key"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or missing API key"}


def test_analyze_audio_works_with_correct_api_key_when_required(client, monkeypatch):
    _enable_api_key(monkeypatch, key="correct-test-key")

    response = _post_audio(client, headers={"X-API-Key": "correct-test-key"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"]
    assert payload["status"]["acoustic_metrics_status"] == "real"
    assert payload["status"]["transcription_status"] == "real"
    assert payload["status"]["emotion_status"] != "mocked"


def test_public_endpoints_do_not_require_api_key(client, monkeypatch):
    _enable_api_key(monkeypatch)

    health = client.get("/health")
    status = client.get("/v1/system/status")
    index = client.get("/")

    assert health.status_code == 200
    assert status.status_code == 200
    assert index.status_code == 200


def test_system_status_does_not_expose_local_or_cohere_keys(client, monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    monkeypatch.setenv("LOCAL_API_KEY", "super-secret-local-key")
    monkeypatch.setenv("COHERE_API_KEY", "super-secret-cohere-key")
    get_settings.cache_clear()

    response = client.get("/v1/system/status")

    assert response.status_code == 200
    assert "super-secret-local-key" not in response.text
    assert "super-secret-cohere-key" not in response.text
    assert "LOCAL_API_KEY" not in response.text
    assert "COHERE_API_KEY" not in response.text


def test_cors_preflight_allows_configured_local_client_origin(client):
    response = client.options(
        "/v1/analyze-audio",
        headers={
            "Origin": "http://127.0.0.1:8020",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:8020"
