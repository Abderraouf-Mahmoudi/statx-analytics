"""Pydantic request and response contracts for the REST API."""

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, HttpUrl, model_validator


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


class TrackingPointCreate(BaseModel):
    player_id: int = Field(gt=0)
    timestamp_seconds: float = Field(
        ge=0,
        validation_alias=AliasChoices("timestamp_seconds", "timestamp"),
    )
    x_coord: float = Field(
        ge=0,
        le=105,
        validation_alias=AliasChoices("x_coord", "x"),
    )
    y_coord: float = Field(
        ge=0,
        le=68,
        validation_alias=AliasChoices("y_coord", "y"),
    )
    speed_kmh: float | None = Field(default=None, ge=0)


class TrackingIngestRequest(BaseModel):
    job_id: str | None = Field(default=None, min_length=1)
    tracking_data: list[TrackingPointCreate] | None = None
    player_mapping: dict[int, int] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_source(self) -> "TrackingIngestRequest":
        if (self.job_id is None) == (self.tracking_data is None):
            raise ValueError("Provide exactly one of job_id or tracking_data")
        if self.tracking_data is not None and not self.tracking_data:
            raise ValueError("tracking_data cannot be empty")
        return self


class TrackingIngestResponse(BaseModel):
    match_id: int
    status: str
    points_ingested: int
    total_points: int
    progress: int
    duration_ms: float


class LaneDistributionResponse(BaseModel):
    left: float
    center: float
    right: float


class PlayerTelemetryResponse(BaseModel):
    player_id: int
    player_name: str
    team_id: int
    distance_km: float
    max_speed_kmh: float
    samples: int


class TacticalAnalysisResponse(BaseModel):
    match_id: int
    perspective_team_id: int
    perspective_team_name: str
    opponent_team_id: int
    opponent_team_name: str
    total_opponent_points: int
    lane_distribution: LaneDistributionResponse
    alerts: list[str]
    player_telemetry: list[PlayerTelemetryResponse]

