"""Paginated provider profile and season-statistics enrichment tests."""

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.model_registry import Base
from app.modules.integrations.api_football import ProviderEnvelope
from app.modules.integrations.player_enrichment import (
    PlayerEnrichmentService,
    PlayerProfilePayloadError,
)
from app.modules.integrations.repository import ProviderRepository, QuotaReserved
from app.modules.organizations.models import Organization, Season, Team
from app.modules.roster.models import Player, PlayerRegistration
from app.modules.roster.statistics_models import PlayerSeasonSnapshot


class PagedClient:
    def __init__(self) -> None:
        self.pages: list[int] = []

    def get(self, endpoint, params):
        page = int(params.get("page", 1))
        self.pages.append(page)
        return ProviderEnvelope(
            response=[{"player": {"id": page}}],
            results=1,
            page=page,
            total_pages=2,
            remaining_quota=90 - page,
        )


def make_domain(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'enrichment.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    organization = Organization(name="StatX Tunis", country_code="TN")
    session.add(organization)
    session.flush()
    team = Team(organization_id=organization.id, name="Espérance ST", provider="api_football", provider_id="1001")
    season = Season(
        organization_id=organization.id,
        name="Ligue 1 2026",
        provider="api_football",
        competition_provider_id="202",
        season_year=2026,
    )
    session.add_all([team, season])
    session.flush()
    player = Player(
        organization_id=organization.id,
        team_id=team.id,
        name="Aymen Ben Ali",
        first_name="Aymen",
        last_name="Ben Ali",
        position="Midfielder",
        provider="api_football",
        provider_id="501",
    )
    session.add(player)
    session.flush()
    session.add(PlayerRegistration(player_id=player.id, team_id=team.id, season_id=season.id, status="active"))
    session.commit()
    return session, organization, team, season, player


def profile_row(*, player_id=501, height="181 cm", weight="76 kg", team_id=1001):
    return {
        "player": {
            "id": player_id,
            "name": "Aymen Ben Ali",
            "firstname": "Aymen",
            "lastname": "Ben Ali",
            "birth": {"date": "2002-03-14", "place": "Tunis", "country": "Tunisia"},
            "nationality": "Tunisia",
            "height": height,
            "weight": weight,
            "photo": "https://media.api-sports.io/football/players/501.png",
        },
        "statistics": [{
            "team": {"id": team_id},
            "league": {"id": 202, "season": 2026},
            "games": {"position": "Midfielder", "appearences": 17, "minutes": 1310},
            "goals": {"total": 4, "assists": 6},
            "passes": {"total": 742, "accuracy": 86},
        }],
    }


def test_cached_pages_follows_provider_pagination_and_is_bounded(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'pages.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        client = PagedClient()
        repository = ProviderRepository(session, client, daily_ceiling=90)
        rows = repository.cached_pages(
            "/players", {"team": 1001, "season": 2026}, timedelta(days=7), max_pages=3
        )
        assert [row["player"]["id"] for row in rows] == [1, 2]
        assert client.pages == [1, 2]


def test_cached_pages_respects_quota_before_requesting_next_page(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{(tmp_path / 'quota-pages.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        client = PagedClient()
        repository = ProviderRepository(session, client, daily_ceiling=1)
        with pytest.raises(QuotaReserved):
            repository.cached_pages(
                "/players", {"team": 1001, "season": 2026}, timedelta(seconds=0), max_pages=3
            )
        assert client.pages == [1]


def test_enrichment_maps_profile_and_persists_versioned_snapshot(tmp_path) -> None:
    session, _, team, season, player = make_domain(tmp_path)
    try:
        summary = PlayerEnrichmentService(session).apply(team, season, [profile_row()])
        session.commit()
        snapshot = session.scalar(select(PlayerSeasonSnapshot))

        assert summary.imported == 1
        assert summary.malformed == 0
        assert player.birth_date == date(2002, 3, 14)
        assert player.birth_place == "Tunis"
        assert player.birth_country == "Tunisia"
        assert player.nationality == "Tunisia"
        assert player.height_cm == 181
        assert player.weight_kg == 76
        assert player.primary_position == "CM"
        assert snapshot.schema_version == 1
        assert snapshot.statistics_json["games"]["appearences"] == 17
        assert "headers" not in snapshot.raw_payload
        assert "api_key" not in str(snapshot.raw_payload).lower()
    finally:
        session.close()


def test_transfer_reuses_identity_creates_registration_and_preserves_overrides(tmp_path) -> None:
    session, organization, _, season, player = make_domain(tmp_path)
    new_team = Team(organization_id=organization.id, name="Club Africain", provider="api_football", provider_id="1002")
    session.add(new_team)
    session.commit()
    player.display_name = "Nom Club"
    player.player_field_overrides = {"display_name": True, "height_cm": True}
    player.height_cm = 179

    try:
        summary = PlayerEnrichmentService(session).apply(
            new_team,
            season,
            [profile_row(team_id=1002)],
        )
        session.commit()

        assert summary.imported == 1
        assert session.query(Player).count() == 1
        assert player.display_name == "Nom Club"
        assert player.height_cm == 179
        assert player.team_id == new_team.id
        assert session.query(PlayerRegistration).count() == 2
    finally:
        session.close()


def test_duplicate_ids_are_rejected_and_impossible_measurements_are_skipped(tmp_path) -> None:
    session, _, team, season, player = make_domain(tmp_path)
    original_height = player.height_cm
    try:
        with pytest.raises(PlayerProfilePayloadError, match="Duplicate provider player id"):
            PlayerEnrichmentService(session).apply(team, season, [profile_row(), profile_row()])
        session.rollback()

        summary = PlayerEnrichmentService(session).apply(
            team,
            season,
            [profile_row(height="999 cm", weight="800 kg")],
        )
        session.commit()
        assert summary.imported == 0
        assert summary.malformed == 1
        assert player.height_cm == original_height
        assert session.query(Player).count() == 1
    finally:
        session.close()
