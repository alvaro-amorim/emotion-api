from tests.conftest import make_wav_bytes


def test_analyze_audio_rejects_invalid_extension(client):
    response = client.post(
        "/v1/analyze-audio",
        files={"file": ("audio.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Formato de áudio não suportado. Envie mp3, wav, m4a, webm ou ogg."
    }


def test_analyze_audio_accepts_webm_extension(client):
    response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "recorded-audio.webm",
                make_wav_bytes(duration_seconds=0.8, amplitude=0.2),
                "audio/webm",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["metadata"]["file_name"] == "recorded-audio.webm"
    assert payload["analysis_id"]


def test_analyze_audio_rejects_corrupted_audio_with_controlled_error(client):
    response = client.post(
        "/v1/analyze-audio",
        files={"file": ("broken.wav", b"not a real wav", "audio/wav")},
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Não foi possível converter o áudio. Verifique se o arquivo é válido."
    )


def test_analyze_audio_returns_controlled_transcription_error(client, monkeypatch):
    from app.api import routes_audio
    from app.core.errors import TranscriptionError

    def fail_transcription(processed_audio, acoustic_metrics, language, settings):
        raise TranscriptionError()

    monkeypatch.setattr(routes_audio, "transcribe_audio", fail_transcription)

    response = client.post(
        "/v1/analyze-audio",
        files={
            "file": (
                "transcription-fails.wav",
                make_wav_bytes(duration_seconds=0.8, amplitude=0.2),
                "audio/wav",
            )
        },
        data={"use_external_ai": "false"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Não foi possível transcrever o áudio. Verifique a qualidade do arquivo."
    )
