from pathlib import Path

import pytest


pytestmark = pytest.mark.real_audio

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "audio"
FIXTURE_NAMES = [
    "ptbr_01_calmo_normal.m4a",
    "ptbr_02_urgente_enfatico.m4a",
    "ptbr_03_baixo_pausado.m4a",
]


def test_reference_audio_fixtures_exist():
    for fixture_name in FIXTURE_NAMES:
        fixture_path = FIXTURE_DIR / fixture_name
        assert fixture_path.exists(), f"Fixture ausente: {fixture_path}"
        assert fixture_path.stat().st_size > 0


@pytest.mark.parametrize("fixture_name", FIXTURE_NAMES)
def test_m4a_reference_fixture_is_accepted(client, fixture_name):
    fixture_path = FIXTURE_DIR / fixture_name
    with fixture_path.open("rb") as audio_file:
        response = client.post(
            "/v1/analyze-audio",
            files={"file": (fixture_name, audio_file, "audio/mp4")},
            data={
                "language": "pt-BR",
                "use_external_ai": "false",
                "interpretation_style": "interpretative",
            },
        )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["metadata"]["file_name"] == fixture_name
    assert payload["status"]["acoustic_metrics_status"] == "real"
    assert payload["status"]["transcription_status"] == "real"
    assert payload["status"]["emotion_status"] == "fallback_local"
    assert payload["status"]["emotion_analysis_source"] == "local_heuristics"
    assert payload["status"]["emotion_status"] != "mocked"
    assert payload["emotion_debug"]["fallback_used"] is True
    assert payload["emotion_comparison"]["agreement_level"] == "local_only"
    assert payload["emotion_summary"]["primary_emotion"]
    assert payload["annotated_transcription"]["text"]
    assert payload["emotion_evidence"]
    assert payload["transcription"]["text"].strip()
    assert payload["acoustic_metrics"]["duration_seconds"] > 0
    assert isinstance(payload["acoustic_metrics"]["avg_volume_db"], float)
    assert isinstance(payload["acoustic_metrics"]["silence_ratio"], float)


def test_feedback_still_works_after_reference_fixture_analysis(client):
    fixture_path = FIXTURE_DIR / "ptbr_01_calmo_normal.m4a"
    with fixture_path.open("rb") as audio_file:
        analysis_response = client.post(
            "/v1/analyze-audio",
            files={"file": (fixture_path.name, audio_file, "audio/mp4")},
            data={
                "language": "pt-BR",
                "use_external_ai": "false",
                "interpretation_style": "interpretative",
            },
        )
    assert analysis_response.status_code == 201, analysis_response.text

    analysis_id = analysis_response.json()["analysis_id"]
    feedback_response = client.post(
        f"/v1/analyses/{analysis_id}/feedback",
        json={
            "rating": "neutral",
            "is_correct": False,
            "corrected_primary_emotion": "neutralidade",
            "notes": "Teste com fixture real; emocao interpretativa em validacao.",
        },
    )

    assert feedback_response.status_code == 201, feedback_response.text
    payload = feedback_response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["learning_example_created"] is True
