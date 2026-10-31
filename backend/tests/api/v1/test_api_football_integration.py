"""Versioned API-Football route contract tests."""

from app.main import create_app
from app.modules.integrations.schemas import ClubSelectionCommand


def test_api_football_routes_are_composed_and_browser_command_has_no_organization_id() -> None:
    routes = {(route.path, method) for route in create_app().routes if hasattr(route, "methods") for method in route.methods}
    assert {
        ("/api/v1/integrations/api-football/status", "GET"),
        ("/api/v1/integrations/api-football/tunisia/clubs", "GET"),
        ("/api/v1/integrations/api-football/select-club", "POST"),
        ("/api/v1/integrations/api-football/sync", "POST"),
        ("/api/v1/integrations/api-football/sync-runs/{run_id}", "GET"),
    } <= routes
    assert "organization_id" not in ClubSelectionCommand.model_fields
