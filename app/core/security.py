import secrets

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


def require_api_key(request: Request) -> None:
    settings = get_settings()
    if not settings.require_api_key:
        return

    provided_key = request.headers.get(settings.api_key_header_name)
    expected_key = settings.local_api_key
    if not provided_key or not expected_key or not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
