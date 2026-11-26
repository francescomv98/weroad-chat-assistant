"""The API's data shapes. `SearchState` is the search shared by the form and the assistant; the
others describe results, suggested relaxations and the search response."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SortKey = Literal["relevance", "price", "date", "rating"]
PhysicalRating = Literal["LOW", "MEDIUM", "HIGH"]
AgeBand = Literal["18-25", "25-35", "25-49"]


class Moods(BaseModel):
    """Minimum mood scores (0-100). Only set the moods the user cares about."""

    party: int | None = Field(None, ge=0, le=100)
    relax: int | None = Field(None, ge=0, le=100)
    nature: int | None = Field(None, ge=0, le=100)
    culture: int | None = Field(None, ge=0, le=100)
    history: int | None = Field(None, ge=0, le=100)

    def active(self) -> dict[str, int]:
        return {k: v for k, v in self.model_dump().items() if v is not None}


class SearchState(BaseModel):
    """The single source of truth for "what the user is looking for".

    The search page form and the assistant both read and write this object.
    Every field is optional; an empty state means "show everything bookable".
    """

    text: str | None = None
    text_match: Literal["all", "any"] = "all"  # "all" = every word must match
    date_from: date | None = None
    date_to: date | None = None
    max_price: int | None = Field(None, gt=0)
    min_days: int | None = Field(None, gt=0)
    max_days: int | None = Field(None, gt=0)
    continents: list[str] = Field(default_factory=list)
    destinations: list[str] = Field(default_factory=list)
    travel_types: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    moods: Moods = Field(default_factory=Moods)
    physical_ratings: list[PhysicalRating] = Field(default_factory=list)
    age_bands: list[AgeBand] = Field(default_factory=list)
    sort: SortKey = "relevance"

    @model_validator(mode="after")
    def _check_ranges(self) -> SearchState:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be before date_to")
        if self.min_days and self.max_days and self.min_days > self.max_days:
            raise ValueError("min_days must be <= max_days")
        return self

    def describe(self) -> list[str]:
        """Human-readable list of active constraints."""
        out = []
        if self.text:
            out.append(f'text "{self.text}"' + (" (any word)" if self.text_match == "any" else ""))
        if self.date_from or self.date_to:
            out.append(f"dates {self.date_from or '…'} → {self.date_to or '…'}")
        if self.max_price:
            out.append(f"≤ €{self.max_price}")
        if self.min_days or self.max_days:
            out.append(f"{self.min_days or 1}–{self.max_days or '∞'} days")
        for label, values in (
            ("continent", self.continents),
            ("destination", self.destinations),
            ("type", self.travel_types),
            ("must have", self.must_have),
            ("physical", self.physical_ratings),
            ("age", self.age_bands)
        ):
            if values:
                out.append(f"{label}: {', '.join(values)}")
        for mood, minimum in self.moods.active().items():
            out.append(f"{mood} ≥ {minimum}")
        return out


class DepartureOut(BaseModel):
    id: str
    start: date
    end: date
    price_eur: int
    base_price_eur: int | None
    status: str
    seats_left: int
    age_band: str


class TripResult(BaseModel):
    trip_id: int
    title: str
    destination: str
    continent: str
    days: int
    url: str
    rating: float | None
    short_description: str
    travel_types: list[str]
    from_price_eur: int
    departures: list[DepartureOut]
    score: float
    matched_terms: list[str] = Field(default_factory=list)


class Relaxation(BaseModel):
    """A suggested change to the search that turns zero results into some."""

    description: str
    relaxed_fields: list[str]
    state: SearchState
    result_count: int


class SearchResponse(BaseModel):
    state: SearchState
    total: int
    results: list[TripResult]
    relaxations: list[Relaxation] = Field(default_factory=list)
    closest: list[TripResult] = Field(default_factory=list)
