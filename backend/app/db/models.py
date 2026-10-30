"""Compatibility exports for the modular StatX domain model."""

from app.modules.identity.models import Membership, User
from app.modules.matches.models import Event, Match, TrackingPoint
from app.modules.organizations.models import Organization, Season, Team, TeamSeason
from app.modules.platform.models import AuditLog, SystemState
from app.modules.roster.models import Consent, Player, PlayerRegistration

__all__ = [
    "AuditLog",
    "Consent",
    "Event",
    "Match",
    "Membership",
    "Organization",
    "Player",
    "PlayerRegistration",
    "Season",
    "SystemState",
    "Team",
    "TeamSeason",
    "TrackingPoint",
    "User",
]
