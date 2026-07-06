from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "audio" / "ptbr_01_calmo_normal.m4a"


def _is_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def build_api_headers(
    *,
    require_api_key: bool,
    api_key: str | None,
    header_name: str | None,
) -> dict[str, str]:
    normalized_key = (api_key or "").strip()
    normalized_header_name = (header_name or "X-API-Key").strip() or "X-API-Key"
    if require_api_key and not normalized_key:
        raise ValueError("REQUIRE_API_KEY=true, mas LOCAL_API_KEY nao esta configurado.")
    if not normalized_key:
        return {}
    return {normalized_header_name: normalized_key}


def main() -> int:
    load_dotenv(ROOT_DIR / ".env", override=False)

    api_url = os.getenv("AUDIO_EMOTION_API_URL", "http://127.0.0.1:8014").rstrip("/")
    require_api_key = _is_truthy(os.getenv("REQUIRE_API_KEY", "false"))
    api_key = os.getenv("LOCAL_API_KEY", "")
    header_name = os.getenv("API_KEY_HEADER_NAME", "X-API-Key")

    if not FIXTURE_PATH.exists():
        print(f"Fixture nao encontrada: {FIXTURE_PATH}", file=sys.stderr)
        return 1

    try:
        headers = build_api_headers(
            require_api_key=require_api_key,
            api_key=api_key,
            header_name=header_name,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        with FIXTURE_PATH.open("rb") as audio_file:
            response = httpx.post(
                f"{api_url}/v1/analyze-audio",
                headers=headers,
                files={"file": (FIXTURE_PATH.name, audio_file, "audio/mp4")},
                data={
                    "language": "pt-BR",
                    "use_external_ai": "false",
                    "interpretation_style": "interpretative",
                },
                timeout=180,
            )
    except httpx.HTTPError as exc:
        print(f"Falha ao chamar Audio Emotion API em {api_url}: {exc}", file=sys.stderr)
        return 2

    print(f"status_code: {response.status_code}")
    if response.status_code == 401:
        print("Erro: API Key ausente ou invalida. Configure LOCAL_API_KEY ou desative REQUIRE_API_KEY.")
        return 1
    if response.status_code >= 400:
        print(response.text)
        return 1

    payload = response.json()
    emotion_summary = payload.get("emotion_summary", {})
    status = payload.get("status", {})
    print(f"analysis_id: {payload.get('analysis_id')}")
    print(f"transcription_status: {status.get('transcription_status')}")
    print(f"emotion_status: {status.get('emotion_status')}")
    print(f"primary_emotion: {emotion_summary.get('primary_emotion')}")
    print(
        "recommended_context_for_ai_agent: "
        f"{payload.get('recommended_context_for_ai_agent', '')[:500]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
