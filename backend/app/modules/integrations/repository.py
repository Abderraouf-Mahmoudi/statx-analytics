"""Persistent provider response cache and conservative daily quota accounting."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.integrations.api_football import ApiFootballClient, ProviderEnvelope, Scalar
from app.modules.integrations.models import ProviderCacheEntry, ProviderQuotaDay


class QuotaReserved(RuntimeError):
    """Raised before a call that would consume the safety reserve."""


@dataclass(frozen=True)
class QuotaSnapshot:
    calls_used: int
    remaining: int


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
            payload = cached.response_json
            quota = self.quota_snapshot(now=moment)
            return ProviderEnvelope(
                response=payload["response"],
                results=payload["results"],
                page=payload["page"],
                total_pages=payload["total_pages"],
                remaining_quota=quota.remaining,
            )

        quota = self._quota_row(moment)
        if quota.calls_used >= self.daily_ceiling:
            raise QuotaReserved("Daily provider safety ceiling reached")
        quota.calls_used += 1
        quota.updated_at = moment
        self.session.flush()

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
