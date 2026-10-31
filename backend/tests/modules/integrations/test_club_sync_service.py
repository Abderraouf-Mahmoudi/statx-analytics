"""Transactional Tunisian club synchronization tests."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.model_registry import Base
from app.modules.integrations.api_football import ProviderEnvelope
from app.modules.integrations.schemas import ClubSelectionCommand
from app.modules.integrations.service import (
    ClubSyncService,
    InvalidProviderPayload,
)
from app.modules.integrations.worker import claim_sync_run
from app.modules.matches.models import Match
from app.modules.organizations.models import Organization, Team
from app.modules.roster.models import Player, PlayerRegistration


class FakeRepository:
    def __init__(self, responses: dict[str, list[dict]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict]] = []

    def cached_request(self, endpoint, params, ttl: timedelta, *, now=None):
        self.calls.append((endpoint, dict(params)))
        payload = self.responses[endpoint]
        return ProviderEnvelope(payload, len(payload), 1, 1, 80)


def make_session(tmp_path) -> tuple[Session, Organization]:
    engine = create_engine(f"sqlite:///{(tmp_path / 'sync.db').as_posix()}")
    Base.metadata.create_all(engine)
    session = Session(engine)
    organization = Organization(name="StatX Tunis", country_code="TN")
    session.add(organization)
    session.commit()
    return session, organization


def provider_payloads() -> dict[str, list[dict]]:
    return {
        "/leagues": [{"league": {"id": 202, "name": "Ligue 1"}, "seasons": [{"year": 2026, "current": True, "coverage": {"standings": True}}]}],
        "/teams": [{"team": {"id": 1001, "name": "Espérance ST", "logo": "https://media.api-sports.io/football/teams/1001.png"}}],
        "/players/squads": [{"team": {"id": 1001}, "players": [
            {"id": 501, "name": "Aymen Ben Ali", "age": 24, "number": 8, "position": "Midfielder", "photo": "https://media.api-sports.io/football/players/501.png"},
            {"id": 502, "name": "Sami Trabelsi", "age": 27, "number": 1, "position": "Goalkeeper", "photo": "https://media.api-sports.io/football/players/502.png"},
        ]}],
        "/fixtures": [{"fixture": {"id": 9001, "date": "2026-10-20T18:00:00+00:00", "status": {"short": "FT"}}, "league": {"id": 202, "name": "Ligue 1", "season": 2026}, "teams": {"home": {"id": 1001, "name": "Espérance ST"}, "away": {"id": 1002, "name": "Club Africain"}}, "goals": {"home": 2, "away": 1}}],
        "/standings": [{"league": {"id": 202, "season": 2026, "standings": [[{"rank": 1, "team": {"id": 1001}, "points": 31}]]}}],
    }


def selection() -> ClubSelectionCommand:
    return ClubSelectionCommand(
        team_provider_id="1001",
        team_name="Espérance ST",
        logo_url="https://media.api-sports.io/football/teams/1001.png",
        league_provider_id="202",
        league_name="Ligue 1",
        season=2026,
    )


def test_initial_workflow_uses_five_calls_and_refresh_is_idempotent(tmp_path) -> None:
    session, organization = make_session(tmp_path)
    repository = FakeRepository(provider_payloads())
    service = ClubSyncService(session, repository)
    try:
        clubs = service.list_tunisian_clubs()
        run = service.queue_initial_sync(organization.id, selection())
        summary = service.execute_run(run.public_id)
        session.commit()

        assert [club.name for club in clubs] == ["Espérance ST"]
        assert len(repository.calls) == 5
        assert summary == {"teams": 2, "players": 2, "fixtures": 1, "standings": 1, "absent": 0}
        assert session.query(Player).count() == 2
        assert session.query(PlayerRegistration).count() == 2
        assert session.query(Match).count() == 1
        assert session.get(Organization, organization.id).primary_team_id is not None

        second = service.queue_initial_sync(organization.id, selection())
        service.execute_run(second.public_id)
        session.commit()
        assert session.query(Player).count() == 2
        assert session.query(PlayerRegistration).count() == 2
        assert session.query(Match).count() == 1
    finally:
        session.close()


def test_refresh_preserves_local_override_and_marks_missing_provider_player_absent(tmp_path) -> None:
    session, organization = make_session(tmp_path)
    payloads = provider_payloads()
    repository = FakeRepository(payloads)
    service = ClubSyncService(session, repository)
    try:
        first = service.queue_initial_sync(organization.id, selection())
        service.execute_run(first.public_id)
        session.commit()
        edited = session.scalar(select(Player).where(Player.provider_id == "501"))
        edited.first_name = "Nom Club"
        edited.local_override = True
        payloads["/players/squads"][0]["players"] = [payloads["/players/squads"][0]["players"][0]]

        refresh = service.queue_initial_sync(organization.id, selection())
        summary = service.execute_run(refresh.public_id)
        session.commit()

        assert edited.first_name == "Nom Club"
        assert summary["absent"] == 1
        assert session.scalar(select(Player).where(Player.provider_id == "502")).provider_absent
    finally:
        session.close()


def test_invalid_duplicate_provider_identity_rolls_back_domain_changes(tmp_path) -> None:
    session, organization = make_session(tmp_path)
    payloads = provider_payloads()
    payloads["/players/squads"][0]["players"].append(dict(payloads["/players/squads"][0]["players"][0]))
    service = ClubSyncService(session, FakeRepository(payloads))
    run = service.queue_initial_sync(organization.id, selection())

    try:
        try:
            service.execute_run(run.public_id)
        except InvalidProviderPayload:
            session.rollback()
        assert session.query(Team).count() == 0
        assert session.query(Player).count() == 0
    finally:
        session.close()


def test_database_lease_allows_only_one_worker_and_recovers_after_expiry(tmp_path) -> None:
    session, organization = make_session(tmp_path)
    service = ClubSyncService(session, FakeRepository(provider_payloads()))
    run = service.queue_initial_sync(organization.id, selection())
    session.commit()
    competitor = Session(session.get_bind())
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    try:
        claimed = claim_sync_run(session, "worker-a", now=now, lease_seconds=60)
        session.commit()
        assert claimed.public_id == run.public_id
        assert claim_sync_run(competitor, "worker-b", now=now, lease_seconds=60) is None
        competitor.rollback()

        recovered = claim_sync_run(
            competitor, "worker-b", now=now + timedelta(seconds=61), lease_seconds=60
        )
        assert recovered.public_id == run.public_id
    finally:
        competitor.close()
        session.close()
