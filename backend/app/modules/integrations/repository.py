"""Persistent provider response cache and conservative daily quota accounting."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.integrations.api_football import ApiFootballClient, ProviderEnvelope, Scalar
from app.modules.integrations.models import (
    ProviderCacheEntry,
    ProviderQuotaDay,
    ProviderRequestLease,
)


class QuotaReserved(RuntimeError):
    """Raised before a call that would consume the safety reserve."""


@dataclass(frozen=True)
class QuotaSnapshot:
    calls_used: int
    remaining: int


@dataclass(frozen=True)
class CachedProviderResponse:
    envelope: ProviderEnvelope
    stale: bool
    cache_age_seconds: int


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class ProviderRepository:
    provider = "api_football"

    def __init__(
        self,
        session: Session,
        client: ApiFootballClient,
        *,
        daily_ceiling: int,
    ) -> None:
        self.session = session
        self.client = client
        self.daily_ceiling = daily_ceiling

    @staticmethod
    def _cache_identity(endpoint: str, params: Mapping[str, Scalar | None]) -> tuple[str, dict]:
        normalized = {key: value for key, value in sorted(params.items()) if value is not None}
        encoded = json.dumps(
            {"endpoint": endpoint, "params": normalized},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest(), normalized

    def _quota_row(self, now: datetime) -> ProviderQuotaDay:
        quota_date = _utc(now).date()
        row = self.session.scalar(
            select(ProviderQuotaDay).where(
                ProviderQuotaDay.provider == self.provider,
                ProviderQuotaDay.quota_date == quota_date,
            )
        )
        if row is None:
            row = ProviderQuotaDay(provider=self.provider, quota_date=quota_date, calls_used=0)
            self.session.add(row)
            self.session.flush()
        return row

    def quota_snapshot(self, *, now: datetime | None = None) -> QuotaSnapshot:
        row = self._quota_row(now or datetime.now(timezone.utc))
        remaining = (
            row.remaining_reported
            if row.remaining_reported is not None
            else max(0, self.daily_ceiling - row.calls_used)
        )
        return QuotaSnapshot(calls_used=row.calls_used, remaining=remaining)

    def _cache_entry(
        self, endpoint: str, params: Mapping[str, Scalar | None]
    ) -> ProviderCacheEntry | None:
        cache_key, _ = self._cache_identity(endpoint, params)
        return self.session.scalar(
            select(ProviderCacheEntry).where(
                ProviderCacheEntry.provider == self.provider,
                ProviderCacheEntry.cache_key == cache_key,
            )
        )

    @staticmethod
    def _envelope_from_cache(
        cached: ProviderCacheEntry, remaining_quota: int
    ) -> ProviderEnvelope:
        payload = cached.response_json
        return ProviderEnvelope(
            response=payload["response"],
            results=payload["results"],
            page=payload["page"],
            total_pages=payload["total_pages"],
            remaining_quota=remaining_quota,
        )

    def cached_request_with_stale_fallback(
        self,
        endpoint: str,
        params: Mapping[str, Scalar | None],
        ttl: timedelta,
        *,
        now: datetime | None = None,
    ) -> CachedProviderResponse:
        """Return fresh data when possible and an expired cache on provider failure."""
        moment = _utc(now or datetime.now(timezone.utc))
        try:
            envelope = self.cached_request(endpoint, params, ttl, now=moment)
            cached = self._cache_entry(endpoint, params)
            fetched_at = _utc(cached.fetched_at) if cached is not None else moment
            age = max(0, int((moment - fetched_at).total_seconds()))
            return CachedProviderResponse(envelope=envelope, stale=False, cache_age_seconds=age)
        except Exception as exc:
            from app.modules.integrations.api_football import (
                IntegrationDisabled,
                ProviderUnavailable,
            )

            if not isinstance(exc, (IntegrationDisabled, ProviderUnavailable, QuotaReserved)):
                raise
            cached = self._cache_entry(endpoint, params)
            if cached is None:
                raise
            quota = self.quota_snapshot(now=moment)
            age = max(0, int((moment - _utc(cached.fetched_at)).total_seconds()))
            return CachedProviderResponse(
                envelope=self._envelope_from_cache(cached, quota.remaining),
                stale=True,
                cache_age_seconds=age,
            )

    def acquire_request_lease(
        self,
        scope_key: str,
        owner_token: str,
        *,
        now: datetime | None = None,
        ttl: timedelta = timedelta(seconds=30),
    ) -> bool:
        moment = _utc(now or datetime.now(timezone.utc))
        existing = self.session.scalar(
            select(ProviderRequestLease).where(
                ProviderRequestLease.provider == self.provider,
                ProviderRequestLease.scope_key == scope_key,
            )
        )
        if existing is not None:
            if existing.owner_token == owner_token:
                return True
            if _utc(existing.expires_at) > moment:
                return False
            self.session.delete(existing)
            self.session.flush()
        try:
            with self.session.begin_nested():
                self.session.add(
                    ProviderRequestLease(
                        provider=self.provider,
                        scope_key=scope_key,
                        owner_token=owner_token,
                        acquired_at=moment,
                        expires_at=moment + ttl,
                    )
                )
                self.session.flush()
        except IntegrityError:
            return False
        return True

    def release_request_lease(self, scope_key: str, owner_token: str) -> None:
        lease = self.session.scalar(
            select(ProviderRequestLease).where(
                ProviderRequestLease.provider == self.provider,
                ProviderRequestLease.scope_key == scope_key,
                ProviderRequestLease.owner_token == owner_token,
            )
        )
        if lease is not None:
            self.session.delete(lease)
            self.session.flush()

    def cached_request(
        self,
        endpoint: str,
        params: Mapping[str, Scalar | None],
        ttl: timedelta,
        *,
        now: datetime | None = None,
    ) -> ProviderEnvelope:
        moment = _utc(now or datetime.now(timezone.utc))
        cache_key, normalized = self._cache_identity(endpoint, params)
        cached = self.session.scalar(
            select(ProviderCacheEntry).where(
                ProviderCacheEntry.provider == self.provider,
                ProviderCacheEntry.cache_key == cache_key,
            )
        )
        if cached is not None and _utc(cached.expires_at) > moment:
            quota = self.quota_snapshot(now=moment)
            return self._envelope_from_cache(cached, quota.remaining)

        quota = self._quota_row(moment)
        if quota.calls_used >= self.daily_ceiling:
            raise QuotaReserved("Daily provider safety ceiling reached")
        quota.calls_used += 1
        quota.updated_at = moment
        self.session.flush()
        # A failed provider response can still consume the remote quota. Persist
        # the reservation before the network call so a caller rollback cannot
        # accidentally grant the call back.
        self.session.commit()

        envelope = self.client.get(endpoint, normalized)
        if envelope.remaining_quota is not None:
            quota.remaining_reported = envelope.remaining_quota
        stored = {
            "response": envelope.response,
            "results": envelope.results,
            "page": envelope.page,
            "total_pages": envelope.total_pages,
        }
        if cached is None:
            cached = ProviderCacheEntry(
                provider=self.provider,
                cache_key=cache_key,
                endpoint=endpoint,
                parameters_json=normalized,
                response_json=stored,
                fetched_at=moment,
                expires_at=moment + ttl,
            )
            self.session.add(cached)
        else:
            cached.parameters_json = normalized
            cached.response_json = stored
            cached.fetched_at = moment
            cached.expires_at = moment + ttl
        self.session.flush()
        return envelope
