"""Typed, secret-safe API-Football HTTP boundary."""

from dataclasses import dataclass
from typing import Any, Mapping, TypeAlias
from urllib.parse import urlsplit

import httpx

from app.config import Settings


Scalar: TypeAlias = str | int | float | bool


class IntegrationDisabled(RuntimeError):
    """Raised when no provider credential is configured."""


class ProviderUnavailable(RuntimeError):
    """Sanitized provider communication or envelope failure."""


@dataclass(frozen=True)
class ProviderEnvelope:
    response: list[dict[str, Any]]
    results: int
    page: int
    total_pages: int
    remaining_quota: int | None = None


class ApiFootballClient:
    """Call the one allowlisted API host without exposing credentials."""

    provider = "api_football"

    def __init__(self, settings: Settings, *, http_client: httpx.Client | None = None) -> None:
        parsed = urlsplit(settings.api_football_base_url)
        if parsed.scheme != "https" or parsed.hostname != "v3.football.api-sports.io":
            raise ValueError("API-Football base URL must use the approved HTTPS host")
        self._base_url = settings.api_football_base_url.rstrip("/")
        self._key = settings.api_football_key
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(
            timeout=httpx.Timeout(
                connect=settings.api_football_connect_timeout_seconds,
                read=settings.api_football_read_timeout_seconds,
                write=settings.api_football_read_timeout_seconds,
                pool=settings.api_football_connect_timeout_seconds,
            ),
            follow_redirects=False,
        )

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def get(self, path: str, params: Mapping[str, Scalar | None]) -> ProviderEnvelope:
        if self._key is None or not self._key.get_secret_value().strip():
            raise IntegrationDisabled("API-Football integration is not configured")
        if not path.startswith("/") or ".." in path:
            raise ValueError("Provider path must be absolute and normalized")
        normalized = {key: value for key, value in sorted(params.items()) if value is not None}
        try:
            response = self._http.get(
                f"{self._base_url}{path}",
                params=normalized,
                headers={"x-apisports-key": self._key.get_secret_value()},
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable("API-Football request failed") from exc
        if response.status_code != 200:
            raise ProviderUnavailable(f"API-Football returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProviderUnavailable("API-Football returned invalid JSON") from exc
        if not isinstance(payload, dict) or payload.get("errors"):
            raise ProviderUnavailable("API-Football returned an error envelope")
        items = payload.get("response")
        paging = payload.get("paging") or {}
        if not isinstance(items, list) or not isinstance(paging, dict):
            raise ProviderUnavailable("API-Football returned an invalid envelope")
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        if remaining is None:
            remaining = response.headers.get("x-ratelimit-remaining")
        try:
            remaining_value = int(remaining) if remaining is not None else None
        except ValueError:
            remaining_value = None
        return ProviderEnvelope(
            response=items,
            results=int(payload.get("results", len(items))),
            page=int(paging.get("current", 1)),
            total_pages=int(paging.get("total", 1)),
            remaining_quota=remaining_value,
        )
