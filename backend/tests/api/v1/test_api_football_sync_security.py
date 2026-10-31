"""Provider status and organization-scope security tests."""

import json

from app.config import Settings
from app.modules.integrations.schemas import IntegrationStatus


def test_status_contract_never_serializes_provider_key(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'security.db').as_posix()}",
        data_root=tmp_path / "data",
        session_secret="test-session-secret-with-enough-entropy",
        api_football_key="do-not-serialize-this-provider-key",
        _env_file=None,
    )
    payload = IntegrationStatus(configured=settings.api_football_key is not None, calls_used=0, remaining=90)
    serialized = json.dumps(payload.model_dump(mode="json"))
    assert serialized == '{"configured": true, "calls_used": 0, "remaining": 90, "selected_team": null, "last_run": null}'
    assert "do-not-serialize" not in serialized
