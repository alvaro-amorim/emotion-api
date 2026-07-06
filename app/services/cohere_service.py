from __future__ import annotations

import json
import re

from app.core.config import Settings, get_settings


class CohereAnalysisError(RuntimeError):
    """Raised when optional Cohere emotion analysis cannot be used safely."""


def should_attempt_external_ai(
    *,
    requested_by_user: bool,
    transcription_text: str,
    settings: Settings | None = None,
) -> bool:
    settings = settings or get_settings()
    provider = settings.emotion_analysis_provider.strip().lower()
    if provider in {"local", "local_fallback", "local_heuristics"}:
        return False
    return requested_by_user and settings.external_ai_available and bool(transcription_text.strip())


def generate_cohere_emotion_analysis(
    *,
    prompt: str,
    settings: Settings | None = None,
) -> dict:
    settings = settings or get_settings()
    if not settings.external_ai_available:
        raise CohereAnalysisError("Cohere nao configurada para esta execucao.")

    try:
        import cohere
    except Exception as exc:  # pragma: no cover - depends on optional package
        raise CohereAnalysisError("SDK da Cohere nao esta instalado.") from exc

    try:
        client = cohere.ClientV2(api_key=settings.cohere_api_key)
        response = client.chat(
            model=settings.cohere_chat_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = _extract_response_text(response)
        return _parse_json_object(text)
    except CohereAnalysisError:
        raise
    except Exception as exc:
        raise CohereAnalysisError("Falha ao chamar ou interpretar resposta da Cohere.") from exc


def _extract_response_text(response: object) -> str:
    message = getattr(response, "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, list) and content:
        first = content[0]
        text = getattr(first, "text", None)
        if isinstance(text, str):
            return text
        if isinstance(first, dict) and isinstance(first.get("text"), str):
            return first["text"]

    text = getattr(response, "text", None)
    if isinstance(text, str):
        return text

    raise CohereAnalysisError("Resposta da Cohere sem texto JSON.")


def _parse_json_object(text: str) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise CohereAnalysisError("Resposta da Cohere nao contem JSON valido.") from None
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise CohereAnalysisError("Resposta JSON da Cohere nao e um objeto.")
    return parsed
