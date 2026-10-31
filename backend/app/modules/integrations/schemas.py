"""Sanitized external-provider contracts shared by services and API routes."""

from pydantic import BaseModel, ConfigDict, HttpUrl


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
