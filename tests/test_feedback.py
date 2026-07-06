from sqlmodel import Session

from app.db.repository import find_similar_learning_examples
from app.db.session import get_engine
from tests.conftest import create_mock_analysis


def _submit_feedback(
    client,
    analysis_id: str,
    *,
    approved_for_learning: bool = True,
    corrected_primary_emotion: str = "ansiedade leve",
):
    return client.post(
        f"/v1/analyses/{analysis_id}/feedback",
        json={
            "rating": "negative",
            "is_correct": False,
            "corrected_primary_emotion": corrected_primary_emotion,
            "corrected_secondary_emotions": ["inseguranca"],
            "corrected_intention": "pedido de ajuda tecnica",
            "corrected_tone": "calmo, mas inseguro",
            "correction_reason": "A analise exagerou a urgencia.",
            "approved_for_learning": approved_for_learning,
            "notes": "A analise exagerou a irritacao.",
        },
    )


def test_feedback_is_saved_and_creates_learning_example(client):
    analysis = create_mock_analysis(client)
    analysis_id = analysis["analysis_id"]

    response = _submit_feedback(client, analysis_id)

    assert response.status_code == 201
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["rating"] == "negative"
    assert payload["learning_example_created"] is True

    examples = client.get("/v1/learning/examples")
    assert examples.status_code == 200
    examples_payload = examples.json()
    assert examples_payload["count"] == 1
    example = examples_payload["examples"][0]
    assert example["source_analysis_id"] == analysis_id
    assert example["original_primary_emotion"]
    assert example["original_secondary_emotions"]
    assert example["original_tone"]
    assert example["corrected_primary_emotion"] == "ansiedade leve"
    assert example["corrected_tone"] == "calmo, mas inseguro"
    assert example["correction_reason"] == "A analise exagerou a urgencia."
    assert example["metrics_snapshot"]["acoustic_metrics"]
    assert example["acoustic_metrics_snapshot"]
    assert example["speech_rate_snapshot"]
    assert example["transcription_excerpt"]
    assert example["emotion_status"] != "mocked"
    assert example["approved_for_reuse"] is True


def test_feedback_updates_learning_example_for_same_analysis_instead_of_duplicating(client):
    analysis = create_mock_analysis(client)
    analysis_id = analysis["analysis_id"]

    first = _submit_feedback(client, analysis_id, corrected_primary_emotion="ansiedade leve")
    second = _submit_feedback(client, analysis_id, corrected_primary_emotion="inseguranca")

    assert first.status_code == 201
    assert second.status_code == 201
    examples = client.get("/v1/learning/examples").json()["examples"]
    assert len(examples) == 1
    assert examples[0]["source_analysis_id"] == analysis_id
    assert examples[0]["corrected_primary_emotion"] == "inseguranca"
    assert examples[0]["updated_at"] is not None


def test_learning_example_ranking_prefers_approved_and_returns_similarity_details(client):
    approved_analysis = create_mock_analysis(client)
    unapproved_analysis = create_mock_analysis(client)
    _submit_feedback(client, approved_analysis["analysis_id"], approved_for_learning=True, corrected_primary_emotion="calma")
    _submit_feedback(
        client,
        unapproved_analysis["analysis_id"],
        approved_for_learning=False,
        corrected_primary_emotion="urgencia",
    )

    with Session(get_engine()) as session:
        examples = find_similar_learning_examples(
            session,
            text=approved_analysis["transcription"]["text"],
            acoustic_metrics=approved_analysis["acoustic_metrics"],
            speech_metrics={
                "words_per_minute": approved_analysis["transcription"]["words_per_minute"],
                "word_count": approved_analysis["transcription"]["word_count"],
            },
            limit=2,
            min_similarity=0.0,
            include_unapproved=True,
        )

    assert examples
    assert examples[0].approved_for_reuse is True
    assert examples[0].similarity_score > 0
    assert examples[0].text_similarity >= 0
    assert examples[0].metric_similarity >= 0
    assert examples[0].reason_used


def test_learning_context_endpoint_returns_similar_examples(client):
    analysis = create_mock_analysis(client)
    analysis_id = analysis["analysis_id"]
    _submit_feedback(client, analysis_id, approved_for_learning=True, corrected_primary_emotion="calma")

    response = client.get(f"/v1/analyses/{analysis_id}/learning-context")

    assert response.status_code == 200
    payload = response.json()
    assert payload["analysis_id"] == analysis_id
    assert payload["count"] >= 1
    assert payload["examples"][0]["similarity_score"] > 0
