"""Versioned organization and roster API surface."""

from app.main import create_app
from app.modules.organizations.schemas import SeasonCommand, TeamCommand
from app.modules.roster.schemas import PlayerCommand


def test_roster_routes_are_versioned_and_uuid_based() -> None:
    paths = {route.path for route in create_app().routes}
    assert {
        "/api/v1/seasons",
        "/api/v1/teams",
        "/api/v1/players",
        "/api/v1/teams/{team_id}/registrations",
        "/api/v1/teams/{team_id}/roster",
        "/api/v1/players/{player_id}/consents",
    }.issubset(paths)


def test_browser_commands_never_accept_organization_identifiers() -> None:
    assert "organization_id" not in SeasonCommand.model_fields
    assert "organization_id" not in TeamCommand.model_fields
    assert "organization_id" not in PlayerCommand.model_fields
