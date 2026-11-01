"""Persistent cache and quota behavior tests."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.model_registry import Base
from app.modules.integrations.api_football import ProviderEnvelope, ProviderUnavailable
from app.modules.integrations.repository import ProviderRepository, QuotaReserved


class FakeClient:
    def __init__(self, remaining: int | None = None) -> None:
        self.calls = 0
        self.remaining = remaining

    def get(self, endpoint: str, params: dict[str, object]) -> ProviderEnvelope:
        self.calls += 1
        return ProviderEnvelope(
            response=[{"endpoint": endpoint, "params": params}],
            results=1,
            page=1,
            total_pages=1,
            remaining_quota=self.remaining,
        )


@pytest.fixture
def session(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'provider.db').as_posix()}")
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        yield value
    engine.dispose()


def test_fresh_cache_hit_consumes_no_additional_call(session: Session) -> None:
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    client = FakeClient(remaining=89)
    repository = ProviderRepository(session, client, daily_ceiling=90)

    first = repository.cached_request("/teams", {"season": 2026, "league": 202}, timedelta(days=7), now=now)
    session.commit()
    second = repository.cached_request("/teams", {"league": 202, "season": 2026}, timedelta(days=7), now=now + timedelta(hours=1))

    assert first.response == second.response
    assert client.calls == 1
    assert repository.quota_snapshot(now=now).calls_used == 1


def test_quota_counter_survives_repository_recreation_and_blocks_call_91(session: Session) -> None:
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    client = FakeClient()
    repository = ProviderRepository(session, client, daily_ceiling=1)
    repository.cached_request("/teams", {"page": 1}, timedelta(seconds=0), now=now)
    session.commit()

    recreated = ProviderRepository(session, client, daily_ceiling=1)
    with pytest.raises(QuotaReserved):
        recreated.cached_request("/teams", {"page": 2}, timedelta(seconds=0), now=now)

    assert client.calls == 1
    assert recreated.quota_snapshot(now=now).calls_used == 1


def test_provider_remaining_header_is_retained(session: Session) -> None:
    now = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
    repository = ProviderRepository(session, FakeClient(remaining=73), daily_ceiling=90)
    repository.cached_request("/leagues", {"country": "Tunisia"}, timedelta(days=7), now=now)
    session.commit()
    assert repository.quota_snapshot(now=now).remaining == 73


def test_failed_remote_call_still_consumes_persisted_quota(session: Session) -> None:
    class FailingClient:
        def get(self, endpoint, params):
            raise ProviderUnavailable("sanitized failure")

    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    repository = ProviderRepository(session, FailingClient(), daily_ceiling=90)
    with pytest.raises(ProviderUnavailable):
        repository.cached_request("/teams", {"league": 202}, timedelta(days=1), now=now)
    session.rollback()
    recreated = ProviderRepository(session, FakeClient(), daily_ceiling=90)
    assert recreated.quota_snapshot(now=now).calls_used == 1


def test_expired_cache_is_returned_as_stale_when_provider_is_unavailable(session: Session) -> None:
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    seed = ProviderRepository(session, FakeClient(), daily_ceiling=90)
    seed.cached_request("/teams", {"league": 202}, timedelta(minutes=1), now=now)
    session.commit()

    class FailingClient:
        def get(self, endpoint, params):
            raise ProviderUnavailable("sanitized failure")

    repository = ProviderRepository(session, FailingClient(), daily_ceiling=90)
    result = repository.cached_request_with_stale_fallback(
        "/teams", {"league": 202}, timedelta(minutes=1), now=now + timedelta(minutes=2)
    )

    assert result.stale is True
    assert result.cache_age_seconds == 120
    assert result.envelope.response[0]["endpoint"] == "/teams"


def test_request_lease_allows_only_one_refresh_owner(tmp_path) -> None:
    database = tmp_path / "leases.db"
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    Base.metadata.create_all(engine)
    first_session = Session(engine)
    second_session = Session(engine)
    try:
        first = ProviderRepository(first_session, FakeClient(), daily_ceiling=90)
        second = ProviderRepository(second_session, FakeClient(), daily_ceiling=90)

        assert first.acquire_request_lease("setup:tunisia", "owner-1") is True
        first_session.commit()
        assert second.acquire_request_lease("setup:tunisia", "owner-2") is False

        first.release_request_lease("setup:tunisia", "owner-1")
        first_session.commit()
        assert second.acquire_request_lease("setup:tunisia", "owner-2") is True
    finally:
        first_session.close()
        second_session.close()
        engine.dispose()
