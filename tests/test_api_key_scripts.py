import pytest

from app.core.config import get_settings
from scripts import smoke_api_key_client
from scripts import validate_audio_fixtures


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_validate_audio_fixtures_headers_when_api_key_is_required(monkeypatch, capsys):
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    monkeypatch.setenv("LOCAL_API_KEY", "script-secret-key")
    monkeypatch.setenv("API_KEY_HEADER_NAME", "X-Test-Key")
    get_settings.cache_clear()

    headers = validate_audio_fixtures._api_key_headers()
    captured = capsys.readouterr()

    assert headers == {"X-Test-Key": "script-secret-key"}
    assert "script-secret-key" not in captured.out
    assert "script-secret-key" not in captured.err


def test_validate_audio_fixtures_headers_empty_when_api_key_is_disabled(monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "false")
    monkeypatch.setenv("LOCAL_API_KEY", "script-secret-key")
    get_settings.cache_clear()

    assert validate_audio_fixtures._api_key_headers() == {}


def test_validate_audio_fixtures_errors_when_required_key_is_empty(monkeypatch):
    monkeypatch.setenv("REQUIRE_API_KEY", "true")
    monkeypatch.setenv("LOCAL_API_KEY", "")
    get_settings.cache_clear()

    with pytest.raises(RuntimeError, match="LOCAL_API_KEY"):
        validate_audio_fixtures._api_key_headers()


def test_smoke_api_key_client_builds_configured_header(capsys):
    headers = smoke_api_key_client.build_api_headers(
        require_api_key=True,
        api_key="script-secret-key",
        header_name="X-Test-Key",
    )
    captured = capsys.readouterr()

    assert headers == {"X-Test-Key": "script-secret-key"}
    assert "script-secret-key" not in captured.out
    assert "script-secret-key" not in captured.err


def test_smoke_api_key_client_allows_empty_header_when_not_required():
    assert smoke_api_key_client.build_api_headers(
        require_api_key=False,
        api_key="",
        header_name="X-API-Key",
    ) == {}


def test_smoke_api_key_client_errors_when_required_key_is_missing():
    with pytest.raises(ValueError, match="LOCAL_API_KEY"):
        smoke_api_key_client.build_api_headers(
            require_api_key=True,
            api_key="",
            header_name="X-API-Key",
        )
