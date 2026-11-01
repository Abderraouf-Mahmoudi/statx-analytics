"""Validated provider profile and season-statistics enrichment."""

from dataclasses import dataclass
from datetime import date
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.organizations.models import Season, Team
from app.modules.roster.models import Player, PlayerRegistration
from app.modules.roster.positions import normalize_position
from app.modules.roster.statistics_models import PlayerSeasonSnapshot


class PlayerProfilePayloadError(RuntimeError):
    """Raised before writes when the profile collection is ambiguous."""


@dataclass(frozen=True)
class EnrichmentSummary:
    imported: int
    malformed: int
    missing: int


def _measurement(value: object, *, minimum: int, maximum: int) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    match = re.search(r"\d+", str(value))
    if match is None:
        raise ValueError("invalid measurement")
    parsed = int(match.group())
    if parsed < minimum or parsed > maximum:
        raise ValueError("impossible measurement")
    return parsed


def _birth_date(value: object) -> date | None:
    if value is None or str(value).strip() == "":
        return None
    return date.fromisoformat(str(value))


class PlayerEnrichmentService:
    provider = "api_football"

    def __init__(self, session: Session) -> None:
        self.session = session

    def apply(self, team: Team, season: Season, rows: list[dict]) -> EnrichmentSummary:
        identities: list[str] = []
        for row in rows:
            provider_id = str((row.get("player") or {}).get("id") or "").strip()
            if not provider_id:
                raise PlayerProfilePayloadError("Provider profile is missing a player id")
            identities.append(provider_id)
        if len(identities) != len(set(identities)):
            raise PlayerProfilePayloadError("Duplicate provider player id")

        imported = 0
        malformed = 0
        missing = 0
        for row, provider_id in zip(rows, identities, strict=True):
            player = self.session.scalar(
                select(Player).where(
                    Player.organization_id == team.organization_id,
                    Player.provider == self.provider,
                    Player.provider_id == provider_id,
                )
            )
            if player is None:
                missing += 1
                continue
            profile = row.get("player") or {}
            statistics = row.get("statistics") or []
            statistic = next(
                (
                    item
                    for item in statistics
                    if str((item.get("team") or {}).get("id")) == str(team.provider_id)
                    and int((item.get("league") or {}).get("season") or 0)
                    == int(season.season_year or 0)
                ),
                statistics[0] if statistics else {},
            )
            try:
                parsed = {
                    "first_name": str(profile.get("firstname") or "").strip() or None,
                    "last_name": str(profile.get("lastname") or "").strip() or None,
                    "display_name": str(profile.get("name") or "").strip() or None,
                    "birth_date": _birth_date((profile.get("birth") or {}).get("date")),
                    "birth_place": str((profile.get("birth") or {}).get("place") or "").strip() or None,
                    "birth_country": str((profile.get("birth") or {}).get("country") or "").strip() or None,
                    "nationality": str(profile.get("nationality") or "").strip() or None,
                    "height_cm": _measurement(profile.get("height"), minimum=120, maximum=230),
                    "weight_kg": _measurement(profile.get("weight"), minimum=35, maximum=150),
                    "preferred_foot": str(profile.get("foot") or "").strip() or None,
                    "primary_position": normalize_position((statistic.get("games") or {}).get("position")),
                    "provider_photo_url": str(profile.get("photo") or "").strip() or None,
                }
            except (TypeError, ValueError):
                malformed += 1
                continue

            overrides = player.player_field_overrides or {}
            if not player.local_override:
                for field, value in parsed.items():
                    if not overrides.get(field):
                        setattr(player, field, value)
                if parsed["display_name"] and not overrides.get("name"):
                    player.name = parsed["display_name"]
                if not overrides.get("position"):
                    player.position = parsed["primary_position"]
            player.team_id = team.id

            registration = self.session.scalar(
                select(PlayerRegistration).where(
                    PlayerRegistration.player_id == player.id,
                    PlayerRegistration.team_id == team.id,
                    PlayerRegistration.season_id == season.id,
                )
            )
            if registration is None:
                registration = PlayerRegistration(
                    player_id=player.id,
                    team_id=team.id,
                    season_id=season.id,
                    position=parsed["primary_position"],
                    status="active",
                )
                self.session.add(registration)

            snapshot = self.session.scalar(
                select(PlayerSeasonSnapshot).where(
                    PlayerSeasonSnapshot.organization_id == team.organization_id,
                    PlayerSeasonSnapshot.player_id == player.id,
                    PlayerSeasonSnapshot.team_id == team.id,
                    PlayerSeasonSnapshot.season_id == season.id,
                    PlayerSeasonSnapshot.provider == self.provider,
                )
            )
            safe_payload = {
                "provider_player_id": provider_id,
                "team_provider_id": team.provider_id,
                "season": season.season_year,
            }
            if snapshot is None:
                snapshot = PlayerSeasonSnapshot(
                    organization_id=team.organization_id,
                    player_id=player.id,
                    team_id=team.id,
                    season_id=season.id,
                    provider=self.provider,
                    schema_version=1,
                    statistics_json=statistic,
                    raw_payload=safe_payload,
                )
                self.session.add(snapshot)
            else:
                snapshot.schema_version = 1
                snapshot.statistics_json = statistic
                snapshot.raw_payload = safe_payload
            imported += 1
        self.session.flush()
        return EnrichmentSummary(imported=imported, malformed=malformed, missing=missing)
