from __future__ import annotations

import argparse
import sys
import logging
import warnings
from pathlib import Path

warnings.filterwarnings(
    "ignore",
    message="Using `httpx` with `starlette.testclient` is deprecated.*",
)

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402

logging.basicConfig(level=logging.WARNING)
for logger_name in ("faster_whisper", "httpx", "httpcore"):
    logging.getLogger(logger_name).setLevel(logging.WARNING)


FIXTURES = [
    ROOT_DIR / "tests" / "fixtures" / "audio" / "ptbr_01_calmo_normal.m4a",
    ROOT_DIR / "tests" / "fixtures" / "audio" / "ptbr_02_urgente_enfatico.m4a",
    ROOT_DIR / "tests" / "fixtures" / "audio" / "ptbr_03_baixo_pausado.m4a",
]


def _post_audio(client: TestClient, path: Path, *, use_external_ai: bool) -> dict:
    with path.open("rb") as audio_file:
        response = client.post(
            "/v1/analyze-audio",
            files={"file": (path.name, audio_file, "audio/mp4")},
            data={
                "language": "pt-BR",
                "use_external_ai": "true" if use_external_ai else "false",
                "interpretation_style": "interpretative",
            },
        )
    if response.status_code != 201:
        raise RuntimeError(f"{path.name}: HTTP {response.status_code} - {response.text}")
    return response.json()


def _print_summary(path: Path, payload: dict) -> None:
    metrics = payload["acoustic_metrics"]
    transcription = payload["transcription"]
    emotion = payload["emotion_summary"]
    status = payload["status"]
    debug = payload.get("emotion_debug", {})
    comparison = payload.get("emotion_comparison", {})
    text = transcription.get("text", "").replace("\n", " ").strip()
    text_preview = text[:180] + ("..." if len(text) > 180 else "")
    annotated = payload.get("annotated_transcription", {}).get("text", "").replace("\n", " ").strip()
    annotated_preview = annotated[:180] + ("..." if len(annotated) > 180 else "")

    print(f"\n=== {path.name} ===")
    print(f"analysis_id: {payload['analysis_id']}")
    print(f"duration_seconds: {metrics['duration_seconds']}")
    print(f"avg_volume_db: {metrics['avg_volume_db']}")
    print(f"peak_volume_db: {metrics['peak_volume_db']}")
    print(f"silence_ratio: {metrics['silence_ratio']}")
    print(f"peak_count: {metrics['peak_count']}")
    print(f"transcription_status: {status['transcription_status']}")
    print(f"transcription_engine: {transcription.get('transcription_engine')}")
    print(f"transcription_model: {transcription.get('transcription_model')}")
    print(f"emotion_status: {status['emotion_status']}")
    print(f"emotion_analysis_source: {status.get('emotion_analysis_source')}")
    print(f"primary_emotion: {emotion.get('primary_emotion')}")
    print(f"secondary_emotions: {emotion.get('secondary_emotions')}")
    print(f"urgency_level: {emotion.get('urgency_level')}")
    print(f"calmness_level: {emotion.get('calmness_level')}")
    print(f"confidence_score: {emotion.get('confidence_score')}")
    print(f"words_per_minute: {transcription.get('words_per_minute')}")
    print(f"fallback_local_primary_emotion: {comparison.get('local_primary_emotion')}")
    print(f"cohere_primary_emotion: {comparison.get('cohere_primary_emotion') or '<nao usado>'}")
    print(f"agreement_level: {comparison.get('agreement_level')}")
    print(f"fallback_used: {debug.get('fallback_used')}")
    print(f"fallback_reason: {debug.get('fallback_reason') or '<nenhum>'}")
    print(f"cohere_attempted: {debug.get('cohere_attempted')}")
    print(f"cohere_success: {debug.get('cohere_success')}")
    print(f"learning_examples_count: {debug.get('learning_examples_count')}")
    print(f"learning_examples_found: {debug.get('learning_examples_found')}")
    print(f"learning_examples_used_count: {debug.get('learning_examples_used_count')}")
    print(f"learning_influence_summary: {payload.get('learning_influence_summary') or debug.get('learning_influence_summary') or '<nenhuma>'}")
    print(f"whether_learning_changed_result: {payload.get('whether_learning_changed_result')}")
    print(f"learning_examples_used: {len(payload.get('learning_examples_used', []))}")
    for item in (debug.get("top_learning_examples") or [])[:3]:
        print(
            "top_learning_example: "
            f"#{item.get('id')} score={item.get('similarity_score')} "
            f"emotion={item.get('corrected_primary_emotion')} "
            f"reason={item.get('reason_used')}"
        )
    print(f"transcription_preview: {text_preview or '<vazia>'}")
    print(f"annotated_preview: {annotated_preview or '<vazia>'}")


def _print_comparisons(results: dict[str, dict]) -> None:
    calm = results["ptbr_01_calmo_normal.m4a"]["acoustic_metrics"]
    urgent = results["ptbr_02_urgente_enfatico.m4a"]["acoustic_metrics"]
    paused = results["ptbr_03_baixo_pausado.m4a"]["acoustic_metrics"]

    print("\n=== Comparacoes acusticas flexiveis ===")
    print(
        "urgente vs calmo: "
        f"peak_count {urgent['peak_count']} vs {calm['peak_count']} | "
        f"peak_volume_db {urgent['peak_volume_db']} vs {calm['peak_volume_db']}"
    )
    print(
        "baixo/pausado vs calmo: "
        f"avg_volume_db {paused['avg_volume_db']} vs {calm['avg_volume_db']} | "
        f"silence_ratio {paused['silence_ratio']} vs {calm['silence_ratio']}"
    )
    print("Use estas comparacoes como tendencia, nao como assercao rigida.")


def _print_emotion_table(results: dict[str, dict]) -> None:
    print("\n=== Resumo comparativo emocional ===")
    header = (
        f"{'arquivo':34} | {'duracao':>7} | {'vol_med':>7} | {'sil':>5} | "
        f"{'wpm':>7} | {'primaria':14} | {'fonte':16} | {'learn':>5} | {'changed':>7} | "
        f"{'fallback':14} | {'cohere':14} | {'agree':10}"
    )
    print(header)
    print("-" * len(header))
    for file_name, payload in results.items():
        metrics = payload["acoustic_metrics"]
        transcription = payload["transcription"]
        emotion = payload["emotion_summary"]
        status = payload["status"]
        comparison = payload.get("emotion_comparison", {})
        debug = payload.get("emotion_debug", {})
        print(
            f"{file_name:34} | "
            f"{metrics['duration_seconds']:7.2f} | "
            f"{metrics['avg_volume_db']:7.2f} | "
            f"{metrics['silence_ratio']:5.2f} | "
            f"{transcription.get('words_per_minute', 0):7.2f} | "
            f"{emotion.get('primary_emotion', '')[:14]:14} | "
            f"{(status.get('emotion_analysis_source') or '')[:16]:16} | "
            f"{debug.get('learning_examples_used_count') or 0:5} | "
            f"{str(payload.get('whether_learning_changed_result'))[:7]:>7} | "
            f"{(comparison.get('local_primary_emotion') or '')[:14]:14} | "
            f"{(comparison.get('cohere_primary_emotion') or '-')[:14]:14} | "
            f"{(comparison.get('agreement_level') or '')[:10]:10}"
        )


def _print_system_status(label: str, status: dict) -> None:
    print(f"\n=== Status do sistema ({label}) ===")
    print(f"app_version: {status.get('version')}")
    print(f"environment: {status.get('environment')}")
    print(f"transcription_engine: {status.get('transcription_engine')}")
    print(f"whisper_model_size: {status.get('whisper_model_size')}")
    print(f"emotion_provider: {status.get('emotion_provider')}")
    print(f"cohere_enabled: {status.get('cohere_enabled')}")
    print(f"cohere_configured: {status.get('cohere_configured')}")
    print(f"ffmpeg_available: {status.get('ffmpeg_available')}")
    print(f"analyses_count: {status.get('analyses_count')}")
    print(f"learning_examples_count: {status.get('learning_examples_count')}")


def _get_system_status(client: TestClient) -> dict:
    response = client.get("/v1/system/status")
    if response.status_code != 200:
        raise RuntimeError(f"/v1/system/status falhou: HTTP {response.status_code} - {response.text}")
    return response.json()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida fixtures reais de audio pelo pipeline local.")
    parser.add_argument(
        "--no-cohere",
        action="store_true",
        help="Forca use_external_ai=false nas requisicoes sem alterar permanentemente o .env.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    use_external_ai = not args.no_cohere

    missing = [path for path in FIXTURES if not path.exists()]
    if missing:
        for path in missing:
            print(f"Fixture nao encontrada: {path}", file=sys.stderr)
        return 1

    print(f"Modo de IA externa: {'habilitado pela requisicao' if use_external_ai else 'desabilitado (--no-cohere)'}")
    results: dict[str, dict] = {}
    with TestClient(app) as client:
        health_response = client.get("/health")
        if health_response.status_code != 200:
            raise RuntimeError(f"/health falhou: HTTP {health_response.status_code} - {health_response.text}")
        health = health_response.json()
        print(f"API: {health.get('app')} {health.get('version')} | env={health.get('environment')}")
        print(f"Cohere disponivel pela configuracao: {health.get('cohere_enabled')}")
        before_status = _get_system_status(client)
        _print_system_status("antes", before_status)
        for path in FIXTURES:
            payload = _post_audio(client, path, use_external_ai=use_external_ai)
            results[path.name] = payload
            _print_summary(path, payload)
        after_status = _get_system_status(client)
        _print_system_status("depois", after_status)
        print(
            "learning_examples_delta: "
            f"{after_status.get('learning_examples_count', 0) - before_status.get('learning_examples_count', 0)}"
        )

    _print_comparisons(results)
    _print_emotion_table(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
