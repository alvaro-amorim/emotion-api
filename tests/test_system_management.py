import json
import os
import subprocess
import sys
from pathlib import Path

from tests.conftest import create_mock_analysis


def _submit_feedback(client, analysis_id: str, *, approved_for_learning: bool = True):
    response = client.post(
        f"/v1/analyses/{analysis_id}/feedback",
        json={
            "rating": "neutral",
            "is_correct": False,
            "corrected_primary_emotion": "inseguranca",
            "corrected_tone": "calmo e hesitante",
            "correction_reason": "Validacao de gestao de exemplos.",
            "approved_for_learning": approved_for_learning,
            "notes": "Exemplo criado por teste automatizado.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _sqlite_path_from_env() -> Path:
    database_url = os.environ["DATABASE_URL"]
    assert database_url.startswith("sqlite:///")
    return Path(database_url.removeprefix("sqlite:///"))


def test_system_status_returns_safe_local_diagnostics(client):
    response = client.get("/v1/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["version"].startswith("0.5.")
    assert payload["transcription_engine"] == "faster-whisper"
    assert payload["whisper_model_size"] == "tiny"
    assert payload["cohere_enabled"] is False
    assert payload["cohere_configured"] is False
    assert isinstance(payload["ffmpeg_available"], bool)
    assert payload["analyses_count"] == 0
    assert payload["learning_examples_count"] == 0
    assert "COHERE_API_KEY" not in response.text
    assert "fake-key" not in response.text


def test_learning_examples_filters_and_patch_deactivation(client):
    analysis = create_mock_analysis(client)
    _submit_feedback(client, analysis["analysis_id"], approved_for_learning=True)

    listed = client.get("/v1/learning/examples?approved_only=true&limit=5&corrected_emotion=inseguranca")
    assert listed.status_code == 200
    payload = listed.json()
    assert payload["count"] == 1
    example = payload["examples"][0]
    assert example["approved_for_reuse"] is True

    patched = client.patch(
        f"/v1/learning/examples/{example['id']}",
        json={"approved_for_reuse": False, "user_notes": "Desativado pelo teste."},
    )
    assert patched.status_code == 200
    assert patched.json()["approved_for_reuse"] is False
    assert patched.json()["user_notes"] == "Desativado pelo teste."

    approved_only = client.get("/v1/learning/examples?approved_only=true")
    assert approved_only.status_code == 200
    assert approved_only.json()["count"] == 0


def test_learning_examples_can_be_filtered_by_source_analysis(client):
    analysis = create_mock_analysis(client)
    _submit_feedback(client, analysis["analysis_id"], approved_for_learning=True)

    response = client.get(f"/v1/learning/examples?source_analysis_id={analysis['analysis_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["examples"][0]["source_analysis_id"] == analysis["analysis_id"]


def test_export_learning_dataset_script_writes_valid_jsonl(client, tmp_path):
    analysis = create_mock_analysis(client)
    _submit_feedback(client, analysis["analysis_id"], approved_for_learning=True)
    output_path = tmp_path / "learning_dataset.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_learning_dataset.py",
            "--approved-only",
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Exportados 1 exemplos" in result.stdout
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["analysis_id"] == analysis["analysis_id"]
    assert rows[0]["approved_for_reuse"] is True
    assert rows[0]["acoustic_metrics_snapshot"]
    assert rows[0]["speech_rate_snapshot"]


def test_cleanup_local_data_dry_run_does_not_delete_database(client):
    create_mock_analysis(client)
    database_path = _sqlite_path_from_env()
    assert database_path.exists()

    result = subprocess.run(
        [sys.executable, "scripts/cleanup_local_data.py", "--dry-run"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=True,
    )

    assert "Dry-run" in result.stdout
    assert database_path.exists()


def test_env_and_local_exports_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "\n.env\n" in f"\n{gitignore}"
    assert "\n.venv/" in f"\n{gitignore}"
    assert "\ndata/" in f"\n{gitignore}"
    assert "\nexports/*" in f"\n{gitignore}"
    assert "\ntests/fixtures/audio/*.m4a" in f"\n{gitignore}"
    assert "\ntests/fixtures/audio/*.mp3" in f"\n{gitignore}"
    assert "\n!tests/fixtures/audio/README.md" in f"\n{gitignore}"
