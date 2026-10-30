"""Organization roster commands and public views."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SeasonCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def dates_are_ordered(self) -> "SeasonCommand":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class TeamCommand(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    category: str | None = Field(default=None, max_length=50)
    gender: str | None = Field(default=None, max_length=30)
    logo_url: str | None = Field(default=None, max_length=500)


class SeasonView(SeasonCommand):
    model_config = ConfigDict(from_attributes=True)
    public_id: str


class TeamView(TeamCommand):
    model_config = ConfigDict(from_attributes=True)
    public_id: str

