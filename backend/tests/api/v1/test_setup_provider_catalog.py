"""Public pre-bootstrap Tunisian club catalog contracts."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.api.problems import ProblemException
from app.db.model_registry import Base
from app.main import create_app
from app.modules.integrations.api_football import (
    ProviderEnvelope,
    ProviderSeasonRestricted,
    ProviderUnavailable,
)
from app.modules.integrations.catalog import TunisianClubCatalogService
from app.modules.integrations.repository import CachedProviderResponse, QuotaSnapshot
from app.modules.integrations.setup_router import provider_catalog
from app.modules.platform.models import SystemState


class CatalogRepository:
    def __init__(self, payloads: dict[tuple[str, tuple[tuple[str, object], ...]], CachedProviderResponse | Exception]) -> None:
        self.payloads = payloads
        self.calls: list[tuple[str, dict[str, object]]] = []

    def cached_request_with_stale_fallback(self, endpoint, params, ttl):
        normalized = dict(params)
        self.calls.append((endpoint, normalized))
        key = (endpoint, tuple(sorted(normalized.items())))
        value = self.payloads.get(key)
        if value is None:
            raise ProviderUnavailable("provider unavailable")
        if isinstance(value, Exception):
            raise value
        return value

    def quota_snapshot(self):
        return QuotaSnapshot(calls_used=3, remaining=87)


def cached(response: list[dict], *, stale: bool = False, age: int = 30) -> CachedProviderResponse:
    return CachedProviderResponse(
        envelope=ProviderEnvelope(response=response, results=len(response), page=1, total_pages=1),
        stale=stale,
        cache_age_seconds=age,
    )


def catalog_payloads() -> dict:
    leagues = [
        {"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True}]},
        {"league": {"id": 204, "name": "Coupe de Tunisie"}, "seasons": [{"year": 2026, "current": True}]},
    ]
    return {
        ("/leagues", (("country", "Tunisia"), ("current", "true"))): cached(leagues),
        ("/teams", (("league", 202), ("season", 2026))): cached([
            {"team": {"id": 1, "name": "Espérance ST", "logo": "https://media.api-sports.io/team/1.png"}},
            {"team": {"id": 2, "name": "Club Africain", "logo": None}},
        ]),
        ("/teams", (("league", 204), ("season", 2026))): cached([
            {"team": {"id": 1, "name": "Espérance ST", "logo": "https://media.api-sports.io/team/1.png"}},
            {"team": {"id": 3, "name": "Étoile du Sahel", "logo": None}},
        ], stale=True, age=900),
    }


def test_catalog_deduplicates_teams_across_current_competitions_and_reports_cache_state() -> None:
    result = TunisianClubCatalogService(CatalogRepository(catalog_payloads())).current_catalog()

    assert [club.provider_id for club in result.clubs] == ["2", "1", "3"]
    assert result.clubs[1].league_name == "Ligue 1"
    assert result.clubs[1].season == 2026
    assert result.stale is True
    assert result.cache_age_seconds == 900
    assert result.quota.calls_used == 3
    assert result.quota.remaining == 87
    assert result.historical_fallback is False
    assert result.historical_season is None


def test_catalog_retries_plan_restricted_season_with_historical_fallback() -> None:
    leagues = cached([
        {"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True}]},
    ])
    repository = CatalogRepository({
        ("/leagues", (("country", "Tunisia"), ("current", "true"))): leagues,
        ("/teams", (("league", 202), ("season", 2026))): ProviderSeasonRestricted("restricted"),
        ("/teams", (("league", 202), ("season", 2024))): cached([
            {"team": {"id": 1, "name": "Espérance ST", "logo": None}},
        ]),
    })

    result = TunisianClubCatalogService(
        repository, historical_fallback_season=2024
    ).current_catalog()

    assert [(club.name, club.season) for club in result.clubs] == [("Espérance ST", 2024)]
    assert result.historical_fallback is True
    assert result.historical_season == 2024
    assert repository.calls[-1] == ("/teams", {"league": 202, "season": 2024})


def test_catalog_does_not_fallback_for_generic_provider_failure() -> None:
    repository = CatalogRepository({
        ("/leagues", (("country", "Tunisia"), ("current", "true"))): cached([
            {"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True}]},
        ]),
        ("/teams", (("league", 202), ("season", 2026))): ProviderUnavailable("provider unavailable"),
        ("/teams", (("league", 202), ("season", 2024))): cached([]),
    })

    with pytest.raises(ProviderUnavailable, match="provider unavailable"):
        TunisianClubCatalogService(repository).current_catalog()

    assert repository.calls[-1] == ("/teams", {"league": 202, "season": 2026})


def test_catalog_propagates_failed_historical_retry() -> None:
    repository = CatalogRepository({
        ("/leagues", (("country", "Tunisia"), ("current", "true"))): cached([
            {"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True}]},
        ]),
        ("/teams", (("league", 202), ("season", 2026))): ProviderSeasonRestricted("restricted"),
        ("/teams", (("league", 202), ("season", 2024))): ProviderUnavailable("fallback unavailable"),
    })

    with pytest.raises(ProviderUnavailable, match="fallback unavailable"):
        TunisianClubCatalogService(repository).current_catalog()


def test_catalog_keeps_newest_season_for_duplicate_club() -> None:
    repository = CatalogRepository({
        ("/leagues", (("country", "Tunisia"), ("current", "true"))): cached([
            {"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True}]},
            {"league": {"id": 204, "name": "Coupe"}, "seasons": [{"year": 2026, "current": True}]},
        ]),
        ("/teams", (("league", 202), ("season", 2026))): ProviderSeasonRestricted("restricted"),
        ("/teams", (("league", 202), ("season", 2024))): cached([
            {"team": {"id": 1, "name": "Espérance ST", "logo": None}},
        ]),
        ("/teams", (("league", 204), ("season", 2026))): cached([
            {"team": {"id": 1, "name": "Espérance ST", "logo": None}},
        ]),
    })

    result = TunisianClubCatalogService(repository).current_catalog()

    assert len(result.clubs) == 1
    assert result.clubs[0].season == 2026


def test_catalog_without_cache_propagates_sanitized_provider_unavailability() -> None:
    with pytest.raises(ProviderUnavailable, match="provider unavailable"):
        TunisianClubCatalogService(CatalogRepository({})).current_catalog()


def test_public_setup_catalog_is_blocked_after_bootstrap(tmp_path: Path, monkeypatch) -> None:
    engine = create_engine(
        f"sqlite:///{(tmp_path / 'setup-catalog.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(SystemState(id=1, bootstrapped=True))
    session.commit()

    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'unused.db').as_posix()}",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        _env_file=None,
    )
    try:
        with pytest.raises(ProblemException) as raised:
            provider_catalog(db=session, settings=settings)
    finally:
        session.close()
        engine.dispose()

    assert raised.value.status_code == 409
    assert raised.value.code == "setup_complete"


def test_setup_catalog_route_is_public_and_versioned() -> None:
    route = next(route for route in create_app().routes if route.path == "/api/v1/setup/provider-catalog")
    assert "GET" in route.methods
