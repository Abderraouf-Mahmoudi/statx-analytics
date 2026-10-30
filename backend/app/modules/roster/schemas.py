"""Player, registration, consent, and roster contracts."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class PlayerCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    birth_date: date | None = None
    primary_position: str = Field(min_length=1, max_length=50)
    preferred_foot: str | None = Field(default=None, max_length=20)


class RegistrationCommand(BaseModel):
    player_id: str
    season_id: str
    shirt_number: int | None = Field(default=None, ge=0, le=99)
    position: str | None = Field(default=None, max_length=50)
    start_date: date | None = None
    end_date: date | None = None


class ConsentCommand(BaseModel):
    consent_type: str = Field(min_length=1, max_length=40)
    document_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    signed_at: datetime
    guardian_name: str | None = Field(default=None, max_length=160)


class PlayerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: str
    first_name: str | None
    last_name: str | None
    birth_date: date | None
    preferred_foot: str | None


class RegistrationView(BaseModel):
    public_id: str
    player_id: str
    team_id: str
    season_id: str
    shirt_number: int | None
    position: str | None
    status: str


class ConsentView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    public_id: str
    consent_type: str
    status: str
    document_sha256: str | None
    subject_is_minor: bool
    guardian_name: str | None
    signed_at: datetime | None
    revoked_at: datetime | None


class RosterItem(BaseModel):
    player_id: str
    first_name: str
    last_name: str
    shirt_number: int | None
    position: str | None
    publishable: bool

