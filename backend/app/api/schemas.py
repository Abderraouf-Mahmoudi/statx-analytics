"""Pydantic request and response contracts for the REST API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ORMModel(BaseModel):
    """Base schema configured to serialize SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class TeamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    logo_url: HttpUrl | None = None


class TeamRead(ORMModel):
    id: int
    name: str
    logo_url: str | None
    created_at: datetime


class PlayerCreate(BaseModel):
    team_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=120)
    jersey_number: int = Field(ge=0, le=99)
    position: str = Field(min_length=1, max_length=50)
    preferred_foot: Literal["left", "right", "both"] | None = None


class PlayerRead(ORMModel):
    id: int
    team_id: int
    name: str
    jersey_number: int
    position: str
    preferred_foot: str | None


class MatchCreate(BaseModel):
    home_team_id: int = Field(gt=0)
    away_team_id: int = Field(gt=0)
    match_date: datetime
    home_score: int = Field(default=0, ge=0)
    away_score: int = Field(default=0, ge=0)
    competition: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def teams_must_be_distinct(self) -> "MatchCreate":
        if self.home_team_id == self.away_team_id:
            raise ValueError("home_team_id and away_team_id must be different")
        return self


class MatchRead(ORMModel):
    id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime
    home_score: int
    away_score: int
    competition: str


class EventCreate(BaseModel):
    player_id: int = Field(gt=0)
    minute: int = Field(ge=0)
    second: int = Field(default=0, ge=0, le=59)
    type: Literal["shot", "pass", "recovery"]
    x_start: float = Field(ge=0, le=120)
    y_start: float = Field(ge=0, le=80)
    x_end: float | None = Field(default=None, ge=0, le=120)
    y_end: float | None = Field(default=None, ge=0, le=80)
    outcome: str | None = Field(default=None, max_length=50)
    xg_value: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "EventCreate":
        if self.type == "pass" and (self.x_end is None or self.y_end is None):
            raise ValueError("A pass requires x_end and y_end coordinates")
        if self.type != "shot" and self.xg_value is not None:
            raise ValueError("xg_value is only valid for shot events")
        return self


class EventRead(ORMModel):
    id: int
    match_id: int
    player_id: int
    minute: int
    second: int
    type: str
    x_start: float
    y_start: float
    x_end: float | None
    y_end: float | None
    outcome: str | None
    xg_value: float | None


class TeamMetrics(BaseModel):
    team_id: int
    team_name: str
    score: int
    total_xg: float
    shots_on_target: int
    possession: float


class AnalyticsResponse(BaseModel):
    match_id: int
    home: TeamMetrics
    away: TeamMetrics
    graphics: dict[str, str]
    tactical_insights: list[str]
    key_player: str | None = None

