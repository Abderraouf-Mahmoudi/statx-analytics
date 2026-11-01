"""Pre-bootstrap, cache-first Tunisian club discovery."""

from datetime import timedelta
from uuid import uuid4

from app.modules.integrations.schemas import (
    ClubCatalog,
    ProviderClub,
    ProviderQuotaSummary,
)


class CatalogRefreshInProgress(RuntimeError):
    """Raised when another process owns the short catalog refresh lease."""


class TunisianClubCatalogService:
    scope_key = "setup:tunisia-club-catalog"

    def __init__(self, repository) -> None:
        self.repository = repository

    def current_catalog(self) -> ClubCatalog:
        owner = str(uuid4())
        leased = True
        if hasattr(self.repository, "acquire_request_lease"):
            leased = self.repository.acquire_request_lease(self.scope_key, owner)
        if not leased:
            raise CatalogRefreshInProgress("The club catalog is currently refreshing")

        stale = False
        greatest_age = 0
        try:
            leagues_result = self.repository.cached_request_with_stale_fallback(
                "/leagues",
                {"country": "Tunisia", "current": "true"},
                timedelta(days=7),
            )
            stale = leagues_result.stale
            greatest_age = leagues_result.cache_age_seconds
            clubs: dict[str, ProviderClub] = {}
            for item in leagues_result.envelope.response:
                league = item.get("league") or {}
                current = next(
                    (row for row in item.get("seasons", []) if row.get("current")),
                    None,
                )
                if current is None or league.get("id") is None:
                    continue
                league_id = str(league["id"])
                season = int(current["year"])
                teams_result = self.repository.cached_request_with_stale_fallback(
                    "/teams",
                    {"league": int(league_id), "season": season},
                    timedelta(days=7),
                )
                stale = stale or teams_result.stale
                greatest_age = max(greatest_age, teams_result.cache_age_seconds)
                for row in teams_result.envelope.response:
                    team = row.get("team") or {}
                    if team.get("id") is None or not str(team.get("name") or "").strip():
                        continue
                    provider_id = str(team["id"])
                    clubs.setdefault(
                        provider_id,
                        ProviderClub(
                            provider_id=provider_id,
                            name=str(team["name"]).strip(),
                            logo_url=team.get("logo"),
                            league_provider_id=league_id,
                            league_name=str(league.get("name") or "Tunisia"),
                            season=season,
                        ),
                    )
            quota = self.repository.quota_snapshot()
            return ClubCatalog(
                clubs=sorted(clubs.values(), key=lambda club: club.name.casefold()),
                stale=stale,
                cache_age_seconds=greatest_age,
                quota=ProviderQuotaSummary(
                    calls_used=quota.calls_used,
                    remaining=quota.remaining,
                ),
            )
        finally:
            if hasattr(self.repository, "release_request_lease"):
                self.repository.release_request_lease(self.scope_key, owner)
