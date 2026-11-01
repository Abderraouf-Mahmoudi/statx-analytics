"""Public commands and views for local identity flows."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


FootballJobTitle = Literal[
    "director",
    "coach",
    "analyst",
    "scout",
    "medical",
    "media",
    "other",
]


class BootstrapCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    organization_name: str = Field(min_length=2, max_length=160)
    admin_display_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=200)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    default_locale: str = Field(default="fr", min_length=2, max_length=10)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    job_title: FootballJobTitle

    @field_validator("country_code")
    @classmethod
    def normalize_country(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("invalid email address")
        return value.lower()


class LoginCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)


class SessionView(BaseModel):
    user_id: str
    organization_id: str
    display_name: str
    email: str
    role: str
    job_title: FootballJobTitle
    locale: str

