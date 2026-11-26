from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from pathlib import Path

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"

BOOKABLE_STATUSES = {"PLANNED", "ALMOST_CONFIRMED", "CONFIRMED", "ALMOST_FULL"}

CONTINENT_FIXES = {
    "Morocco": "Africa",
    "Egypt": "Africa",
    "Tunisia": "Africa",
    "Madagascar": "Africa",
    "Vietnam": "Asia",
    "Indonesia": "Asia",
    "Thailand": "Asia",
    "Philippines": "Asia",
    "Turkey": "Asia",
    "Iceland": "Europe",
    "Sweden": "Europe",
    "Denmark": "Europe",
    "Latvia": "Europe",
    "Puerto Rico": "America",
    "Dominican Republic": "America"
}

MOODS = ("party", "relax", "nature", "culture", "history")


@dataclass(frozen=True)
class Departure:
    id: str
    trip_id: int
    start: date
    end: date
    price_eur: int
    base_price_eur: int | None
    status: str
    seats_left: int
    age_band: str

    def is_bookable(self, today: date) -> bool:
        return self.status in BOOKABLE_STATUSES and self.seats_left > 0 and self.start >= today


@dataclass(frozen=True)
class Trip:
    id: int
    slug: str
    url: str
    title: str
    destination: str
    continent: str
    destination_label: str
    days: int
    travel_style: str
    travel_types: tuple[str, ...]
    moods: dict[str, int]
    physical_rating: str
    short_description: str
    description: str
    rating: float | None
    rating_count: int
    itinerary: tuple[dict, ...]
    departures: tuple[Departure, ...]
    search_blob: str = field(repr=False)


@dataclass(frozen=True)
class Faq:
    id: int
    destination: str | None
    title: str
    body: str
    url: str


def normalise_text(text: str) -> str:
    text = text.lower().replace("’", "'")
    return re.sub(r"\s+", " ", text)


def _build_blob(raw: dict) -> str:
    parts = [
        raw["title"],
        raw["destination"],
        raw.get("destinationLabel") or "",
        raw.get("continent") or "",
        raw.get("startingPlace") or "",
        raw.get("endingPlace") or "",
        " ".join(raw.get("travelTypes") or []),
        raw.get("shortDescription") or "",
        raw.get("description") or ""
    ]

    for day in raw.get("itinerary") or []:
        parts.append(day.get("title") or "")
        parts.append(day.get("nights") or "")
        parts.extend(day.get("highlights") or [])

    return normalise_text(" ".join(parts))


def _parse_trip(raw: dict) -> Trip:
    departures = tuple(
        Departure(
            id=t["id"],
            trip_id=raw["id"],
            start=date.fromisoformat(t["startingDate"]),
            end=date.fromisoformat(t["endingDate"]),
            price_eur=t["priceEur"],
            base_price_eur=t.get("basePriceEur"),
            status=t["salesStatus"],
            seats_left=t["seatsLeft"],
            age_band=t["ageBand"]
        )
        for t in raw.get("tours") or []
    )

    continent = raw.get("continent") or CONTINENT_FIXES.get(raw["destination"], "Other")
    raw = {**raw, "continent": continent}

    return Trip(
        id=raw["id"],
        slug=raw["slug"],
        url=raw["url"],
        title=raw["title"],
        destination=raw["destination"],
        continent=continent,
        destination_label=raw.get("destinationLabel") or raw["destination"],
        days=raw["numberOfDays"],
        travel_style=raw["travelStyle"],
        travel_types=tuple(raw.get("travelTypes") or ()),
        moods={m: int(raw["moods"].get(m, 0)) for m in MOODS},
        physical_rating=raw["physicalRating"],
        short_description=raw.get("shortDescription") or "",
        description=raw.get("description") or "",
        rating=(raw.get("rating") or {}).get("value"),
        rating_count=(raw.get("rating") or {}).get("count", 0),
        itinerary=tuple(raw.get("itinerary") or ()),
        departures=departures,
        search_blob=_build_blob(raw)
    )


@dataclass(frozen=True)
class Catalog:
    trips: tuple[Trip, ...]
    faqs: tuple[Faq, ...]

    def trip(self, trip_id: int) -> Trip | None:
        return next((t for t in self.trips if t.id == trip_id), None)

    @property
    def destinations(self) -> list[str]:
        return sorted({t.destination for t in self.trips})

    @property
    def continents(self) -> list[str]:
        return sorted({t.continent for t in self.trips})

    @property
    def travel_types(self) -> list[str]:
        return sorted({tt for t in self.trips for tt in t.travel_types})


def load_catalog(samples_dir: Path = SAMPLES_DIR) -> Catalog:
    trips_raw = json.loads((samples_dir / "trips.json").read_text(encoding="utf-8"))
    faqs_raw = json.loads((samples_dir / "faqs.json").read_text(encoding="utf-8"))
    trips = tuple(_parse_trip(t) for t in trips_raw["travels"])
    faqs = tuple(
        Faq(id=f["id"], destination=f.get("destination"), title=f["title"], body=f["body"], url=f.get("url", ""))
        for f in faqs_raw["faqs"]
    )
    return Catalog(trips=trips, faqs=faqs)


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    return load_catalog()
