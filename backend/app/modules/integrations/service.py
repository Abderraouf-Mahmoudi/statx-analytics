"""Validation-first, organization-scoped API-Football synchronization."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.identity.service import ResourceNotFound
from app.modules.integrations.models import (
    ProviderStandingSnapshot,
    ProviderSyncRun,
    ProviderSyncStage,
)
from app.modules.integrations.schemas import ClubSelectionCommand, ProviderClub
from app.modules.matches.models import Match
from app.modules.organizations.models import Organization, Season, Team, TeamSeason
from app.modules.platform.audit import write_audit
from app.modules.roster.models import Player, PlayerRegistration


class InvalidProviderPayload(RuntimeError):
    """Raised before domain writes when a provider payload is unsafe to merge."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _id(value: Any) -> str:
    if value is None or str(value).strip() == "":
        raise InvalidProviderPayload("Provider record is missing an immutable id")
    return str(value)


def _split_name(name: str) -> tuple[str, str]:
    parts = name.strip().split(maxsplit=1)
    if not parts:
        raise InvalidProviderPayload("Provider player name is empty")
    return parts[0], parts[1] if len(parts) == 2 else ""


class ClubSyncService:
    provider = "api_football"
    stage_names = ("squad", "profiles", "fixtures", "standings", "portraits")

    def __init__(self, session: Session, repository) -> None:
        self.session = session
        self.repository = repository

    def list_tunisian_clubs(self) -> list[ProviderClub]:
        leagues = self.repository.cached_request(
            "/leagues", {"country": "Tunisia", "current": "true"}, timedelta(days=7)
        ).response
        clubs: dict[str, ProviderClub] = {}
        for item in leagues:
            league = item.get("league") or {}
            current = next((row for row in item.get("seasons", []) if row.get("current")), None)
            if current is None:
                continue
            league_id = _id(league.get("id"))
            season = int(current["year"])
            teams = self.repository.cached_request(
                "/teams", {"league": int(league_id), "season": season}, timedelta(days=7)
            ).response
            for row in teams:
                team = row.get("team") or {}
                team_id = _id(team.get("id"))
                clubs[team_id] = ProviderClub(
                    provider_id=team_id,
                    name=str(team.get("name") or "").strip(),
                    logo_url=team.get("logo"),
                    league_provider_id=league_id,
                    league_name=str(league.get("name") or "Tunisia"),
                    season=season,
                )
        return sorted(clubs.values(), key=lambda club: club.name.casefold())

    def queue_initial_sync(
        self, organization_id: int, command: ClubSelectionCommand
    ) -> ProviderSyncRun:
        if self.session.get(Organization, organization_id) is None:
            raise ResourceNotFound("Resource not found")
        run = ProviderSyncRun(
            organization_id=organization_id,
            provider=self.provider,
            status="queued",
            request_json=command.model_dump(mode="json"),
        )
        self.session.add(run)
        self.session.flush()
        for name in self.stage_names:
            self.session.add(
                ProviderSyncStage(sync_run_id=run.id, name=name, status="pending")
            )
        self.session.flush()
        write_audit(
            self.session,
            actor_id=None,
            organization_id=organization_id,
            action="provider.sync_queued",
            entity_type="provider_sync_run",
            entity_public_id=run.public_id,
            after={"provider": self.provider, "team_provider_id": command.team_provider_id},
        )
        return run

    def execute_run(self, run_public_id: str) -> dict[str, int]:
        run = self.session.scalar(
            select(ProviderSyncRun).where(ProviderSyncRun.public_id == run_public_id)
        )
        if run is None:
            raise ResourceNotFound("Resource not found")
        command = ClubSelectionCommand.model_validate(run.request_json)
        run.status = "processing"
        run.started_at = utc_now()
        self.session.flush()

        squad_stage = self._stage(run, "squad")
        self._start_stage(squad_stage)
        try:
            squad_payload = self.repository.cached_request(
                "/players/squads", {"team": int(command.team_provider_id)}, timedelta(days=7)
            ).response
            players = self._validate_squad(squad_payload, command.team_provider_id)
            self._complete_stage(squad_stage, len(players))
        except Exception as exc:
            self._fail_stage(squad_stage, exc)
            run.status = "failed"
            run.error_summary = type(exc).__name__
            run.completed_at = utc_now()
            self.session.flush()
            raise

        profiles_stage = self._stage(run, "profiles")
        profiles_stage.status = "skipped"
        profiles_stage.completed_at = utc_now()

        fixtures: list[dict] = []
        fixtures_stage = self._stage(run, "fixtures")
        self._start_stage(fixtures_stage)
        try:
            fixture_payload = self.repository.cached_request(
                "/fixtures",
                {
                    "team": int(command.team_provider_id),
                    "league": int(command.league_provider_id),
                    "season": command.season,
                },
                timedelta(minutes=30),
            ).response
            fixtures = self._validate_fixtures(fixture_payload)
            self._complete_stage(fixtures_stage, len(fixtures))
        except Exception as exc:
            self._fail_stage(fixtures_stage, exc)

        standing_payload: list[dict] = []
        standings_stage = self._stage(run, "standings")
        self._start_stage(standings_stage)
        try:
            standing_payload = self.repository.cached_request(
                "/standings",
                {"league": int(command.league_provider_id), "season": command.season},
                timedelta(minutes=30),
            ).response
            self._validate_standings(standing_payload)
            self._complete_stage(standings_stage, len(standing_payload))
        except Exception as exc:
            self._fail_stage(standings_stage, exc)

        try:
            with self.session.begin_nested():
                summary = self._apply_payload(
                    run, command, players, fixtures, standing_payload
                )
        except Exception:
            run.status = "failed"
            run.error_summary = "Validated provider data could not be synchronized"
            run.completed_at = utc_now()
            raise
        run.status = "completed"
        run.result_summary = summary
        run.call_count = 3
        quota = self.repository.quota_snapshot() if hasattr(self.repository, "quota_snapshot") else None
        run.remaining_quota = quota.remaining if quota else None
        run.completed_at = utc_now()
        self.session.flush()
        return summary

    def _stage(self, run: ProviderSyncRun, name: str) -> ProviderSyncStage:
        stage = self.session.scalar(
            select(ProviderSyncStage).where(
                ProviderSyncStage.sync_run_id == run.id,
                ProviderSyncStage.name == name,
            )
        )
        if stage is None:
            stage = ProviderSyncStage(sync_run_id=run.id, name=name, status="pending")
            self.session.add(stage)
            self.session.flush()
        return stage

    @staticmethod
    def _start_stage(stage: ProviderSyncStage) -> None:
        stage.status = "running"
        stage.started_at = utc_now()
        stage.error_summary = None

    @staticmethod
    def _complete_stage(stage: ProviderSyncStage, item_count: int) -> None:
        stage.status = "completed"
        stage.item_count = item_count
        stage.completed_at = utc_now()

    @staticmethod
    def _fail_stage(stage: ProviderSyncStage, exc: Exception) -> None:
        stage.status = "failed"
        stage.error_summary = type(exc).__name__
        stage.completed_at = utc_now()

    @staticmethod
    def _validate_squad(payload: list[dict], selected_team_id: str) -> list[dict]:
        if len(payload) != 1 or _id((payload[0].get("team") or {}).get("id")) != selected_team_id:
            raise InvalidProviderPayload("Squad does not match selected team")
        players = payload[0].get("players")
        if not isinstance(players, list):
            raise InvalidProviderPayload("Squad players are missing")
        seen: set[str] = set()
        for player in players:
            player_id = _id(player.get("id"))
            if player_id in seen:
                raise InvalidProviderPayload("Duplicate provider player id")
            seen.add(player_id)
            _split_name(str(player.get("name") or ""))
        return players

    @staticmethod
    def _validate_fixtures(payload: list[dict]) -> list[dict]:
        seen: set[str] = set()
        for row in payload:
            fixture_id = _id((row.get("fixture") or {}).get("id"))
            if fixture_id in seen:
                raise InvalidProviderPayload("Duplicate provider fixture id")
            seen.add(fixture_id)
            teams = row.get("teams") or {}
            _id((teams.get("home") or {}).get("id"))
            _id((teams.get("away") or {}).get("id"))
        return payload

    @staticmethod
    def _validate_standings(payload: list[dict]) -> None:
        if payload and not isinstance((payload[0].get("league") or {}).get("standings"), list):
            raise InvalidProviderPayload("Standings payload is invalid")

    def _provider_team(self, organization_id: int, data: dict) -> Team:
        provider_id = _id(data.get("id"))
        team = self.session.scalar(
            select(Team).where(
                Team.organization_id == organization_id,
                Team.provider == self.provider,
                Team.provider_id == provider_id,
            )
        )
        if team is None:
            team = Team(
                organization_id=organization_id,
                name=str(data.get("name") or f"Provider team {provider_id}"),
                source=self.provider,
                provider=self.provider,
                provider_id=provider_id,
            )
            self.session.add(team)
        team.logo_source_url = data.get("logo") or team.logo_source_url
        team.provider_updated_at = utc_now()
        self.session.flush()
        return team

    def _apply_payload(
        self,
        run: ProviderSyncRun,
        command: ClubSelectionCommand,
        players: list[dict],
        fixtures: list[dict],
        standings: list[dict],
    ) -> dict[str, int]:
        organization = self.session.get(Organization, run.organization_id)
        season = self.session.scalar(
            select(Season).where(
                Season.organization_id == organization.id,
                Season.provider == self.provider,
                Season.competition_provider_id == command.league_provider_id,
                Season.season_year == command.season,
            )
        )
        if season is None:
            season = Season(
                organization_id=organization.id,
                name=f"{command.league_name} {command.season}",
                provider=self.provider,
                competition_provider_id=command.league_provider_id,
                season_year=command.season,
                start_date=date(command.season, 7, 1),
                end_date=date(command.season + 1, 6, 30),
            )
            self.session.add(season)
            self.session.flush()
        team = self._provider_team(
            organization.id,
            {"id": command.team_provider_id, "name": command.team_name, "logo": str(command.logo_url) if command.logo_url else None},
        )
        if self.session.scalar(select(TeamSeason.id).where(TeamSeason.team_id == team.id, TeamSeason.season_id == season.id)) is None:
            self.session.add(TeamSeason(team_id=team.id, season_id=season.id))
        organization.primary_team_id = team.id
        run.team_id = team.id

        known = {
            player.provider_id: player
            for player in self.session.scalars(
                select(Player).where(
                    Player.organization_id == organization.id,
                    Player.provider == self.provider,
                )
            )
        }
        seen: set[str] = set()
        for row in players:
            provider_id = _id(row.get("id"))
            seen.add(provider_id)
            first_name, last_name = _split_name(str(row.get("name")))
            player = known.get(provider_id)
            if player is None:
                player = Player(
                    organization_id=organization.id,
                    first_name=first_name,
                    last_name=last_name,
                    name=str(row.get("name")),
                    position=str(row.get("position") or "Unknown"),
                    jersey_number=row.get("number"),
                    team_id=team.id,
                    source=self.provider,
                    provider=self.provider,
                    provider_id=provider_id,
                )
                self.session.add(player)
                self.session.flush()
                known[provider_id] = player
            elif not player.local_override:
                player.first_name = first_name
                player.last_name = last_name
                player.name = str(row.get("name"))
                player.position = str(row.get("position") or player.position)
                player.jersey_number = row.get("number")
            player.team_id = team.id
            player.provider_photo_url = row.get("photo")
            player.provider_absent = False
            player.provider_updated_at = utc_now()
            registration = self.session.scalar(
                select(PlayerRegistration).where(
                    PlayerRegistration.player_id == player.id,
                    PlayerRegistration.team_id == team.id,
                    PlayerRegistration.season_id == season.id,
                )
            )
            if registration is None:
                self.session.add(
                    PlayerRegistration(
                        player_id=player.id,
                        team_id=team.id,
                        season_id=season.id,
                        shirt_number=row.get("number"),
                        position=row.get("position"),
                        status="active",
                    )
                )
        absent = 0
        for provider_id, player in known.items():
            if provider_id not in seen and player.team_id == team.id:
                player.provider_absent = True
                absent += 1

        fixture_count = 0
        teams_seen = {team.id}
        for row in fixtures:
            fixture = row["fixture"]
            sides = row["teams"]
            home = self._provider_team(organization.id, sides["home"])
            away = self._provider_team(organization.id, sides["away"])
            teams_seen.update((home.id, away.id))
            provider_id = _id(fixture["id"])
            match = self.session.scalar(
                select(Match).where(Match.provider == self.provider, Match.provider_id == provider_id)
            )
            if match is None:
                match = Match(
                    season_id=season.id,
                    home_team_id=home.id,
                    away_team_id=away.id,
                    match_date=datetime.fromisoformat(fixture["date"].replace("Z", "+00:00")),
                    competition=str((row.get("league") or {}).get("name") or command.league_name),
                    provider=self.provider,
                    provider_id=provider_id,
                )
                self.session.add(match)
            goals = row.get("goals") or {}
            match.home_score = int(goals.get("home") or 0)
            match.away_score = int(goals.get("away") or 0)
            match.status = "completed" if (fixture.get("status") or {}).get("short") == "FT" else "scheduled"
            match.provider_updated_at = utc_now()
            fixture_count += 1

        snapshot = self.session.scalar(
            select(ProviderStandingSnapshot).where(
                ProviderStandingSnapshot.organization_id == organization.id,
                ProviderStandingSnapshot.team_id == team.id,
                ProviderStandingSnapshot.season_id == season.id,
                ProviderStandingSnapshot.provider == self.provider,
            )
        )
        if snapshot is None:
            snapshot = ProviderStandingSnapshot(
                organization_id=organization.id,
                team_id=team.id,
                season_id=season.id,
                provider=self.provider,
                payload={"response": standings},
            )
            self.session.add(snapshot)
        else:
            snapshot.payload = {"response": standings}
            snapshot.captured_at = utc_now()
        self.session.flush()
        return {
            "teams": len(teams_seen),
            "players": len(players),
            "fixtures": fixture_count,
            "standings": 1 if standings else 0,
            "absent": absent,
        }
