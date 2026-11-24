"""Request models and the validation rules that don't depend on which city it is."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.data.cities import PREFS

Mode = Literal["transit", "bike", "car"]
Kind = Literal["food", "drinks"]

MAX_PEOPLE = 8
RADIUS_MIN, RADIUS_MAX, RADIUS_STEP, RADIUS_DEFAULT = 300, 1500, 100, 800


class LatLngIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    city: str = Field(max_length=32)
    modes: list[Mode] = Field(min_length=1, max_length=MAX_PEOPLE)
    kind: Kind
    prefs: list[str] = Field(default_factory=list, max_length=8)
    radius_m: int = Field(ge=RADIUS_MIN, le=RADIUS_MAX)
    selected: str | None = Field(default=None, max_length=64)
    custom: LatLngIn | None = None

    @field_validator("radius_m")
    @classmethod
    def _radius_step(cls, v: int) -> int:
        if v % RADIUS_STEP:
            raise ValueError(f"radius_m must be a multiple of {RADIUS_STEP}")
        return v

    @model_validator(mode="after")
    def _prefs_match_kind(self):
        unknown = set(self.prefs) - set(PREFS[self.kind])
        if unknown:
            raise ValueError(f"unknown {self.kind} preferences: {sorted(unknown)}")
        return self
