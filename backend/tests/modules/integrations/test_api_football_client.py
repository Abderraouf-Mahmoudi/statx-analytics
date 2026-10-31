"""API-Football transport boundary tests."""

import httpx
import pytest

from app.config import Settings
from app.modules.integrations.api_football import (
    ApiFootballClient,
    ProviderUnavailable,
)


def settings(tmp_path, key: str | None = "provider-test-secret") -> Settings:
    return Settings(
        database_url=f"sqlite:///{(tmp_path / 'client.db').as_posix()}",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        api_football_key=key,
        _env_file=None,
    )


def test_client_sends_secret_only_to_exact_provider_host_and_normalizes_params(tmp_path) -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["url"] = str(request.url)
        observed["key"] = request.headers.get("x-apisports-key")
        return httpx.Response(
            200,
            headers={"x-ratelimit-requests-remaining": "87"},
            json={"get": "teams", "parameters": {}, "errors": [], "results": 1, "paging": {"current": 1, "total": 1}, "response": [{"team": {"id": 1}}]},
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    envelope = ApiFootballClient(settings(tmp_path), http_client=http_client).get(
        "/teams", {"season": 2026, "league": 202, "unused": None}
    )

    assert observed == {
        "url": "https://v3.football.api-sports.io/teams?league=202&season=2026",
        "key": "provider-test-secret",
    }
    assert envelope.response == [{"team": {"id": 1}}]
    assert envelope.remaining_quota == 87


def test_client_rejects_redirect_without_leaking_secret(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/steal"})

    client = ApiFootballClient(
        settings(tmp_path), http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderUnavailable) as raised:
        client.get("/teams", {"league": 202})

    assert "provider-test-secret" not in str(raised.value)
    assert "example.com" not in str(raised.value)


def test_client_rejects_provider_error_envelope_and_redacts_key(tmp_path) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"get": "teams", "parameters": {}, "errors": {"token": "Invalid key"}, "results": 0, "paging": {"current": 1, "total": 1}, "response": []},
        )

    client = ApiFootballClient(
        settings(tmp_path), http_client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(ProviderUnavailable) as raised:
        client.get("/teams", {})
    assert "provider-test-secret" not in repr(raised.value)

