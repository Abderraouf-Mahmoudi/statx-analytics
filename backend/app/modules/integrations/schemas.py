"""Sanitized external-provider contracts shared by services and API routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ProviderClub(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    provider_id: str
    name: str
    logo_url: HttpUrl | None = None
    league_provider_id: str
    league_name: str
    season: int


class ProviderPlayer(BaseModel):
    provider_id: str
    name: str
    age: int | None = None
    number: int | None = None
    position: str | None = None
    photo_url: HttpUrl | None = None


class ClubSelectionCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    team_provider_id: str = Field(min_length=1, max_length=80)
    team_name: str = Field(min_length=1, max_length=120)
    logo_url: HttpUrl | None = None
    league_provider_id: str = Field(min_length=1, max_length=80)
    league_name: str = Field(min_length=1, max_length=120)
    season: int = Field(ge=2000, le=2200)


class SyncRunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: str
    status: str
    call_count: int
    remaining_quota: int | None
    result_summary: dict[str, Any] | None
    error_summary: str | None
    created_at: datetime
    completed_at: datetime | None
    stages: list["SyncStageView"] = Field(default_factory=list)


class SyncStageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str
    status: str
    item_count: int
    error_summary: str | None


class SelectedTeamView(BaseModel):
    public_id: str
    name: str
    logo_url: str | None = None


class IntegrationStatus(BaseModel):
    configured: bool
    calls_used: int
    remaining: int
    selected_team: SelectedTeamView | None = None
    last_run: SyncRunView | None = None


class ClubCatalog(BaseModel):
    clubs: list[ProviderClub]
    stale: bool = False
    cache_age_seconds: int | None = None
    quota: "ProviderQuotaSummary"


class ProviderQuotaSummary(BaseModel):
    calls_used: int
    remaining: int
