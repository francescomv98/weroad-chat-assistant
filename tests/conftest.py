from __future__ import annotations

from datetime import date

import pytest

from app import tracing
from app.data import Catalog, Faq, _parse_trip

TODAY = date(2027, 1, 10)


@pytest.fixture(autouse=True)
def no_tracing():
    """Tests never send traces, even when the Langfuse keys are in .env."""
    tracing.configure(enabled=False)


def tour(trip_id, n, start, end, price, status="CONFIRMED", seats=5, age="25-35", base=None):
    return {
        "id": f"{trip_id}-{n}", "startingDate": start, "endingDate": end, "priceEur": price,
        "basePriceEur": base, "salesStatus": status, "seatsLeft": seats, "ageBand": age
    }


def trip(id, title, destination, continent, days, types, moods, physical, text, tours, highlights=()):
    return _parse_trip({
        "id": id, "slug": title.lower().replace(" ", "-"), "url": f"https://example.test/{id}",
        "title": title, "destination": destination, "continent": continent,
        "numberOfDays": days, "travelStyle": "GROUP", "travelTypes": list(types),
        "moods": moods, "physicalRating": physical, "shortDescription": text,
        "description": text, "rating": {"value": 4.5, "count": 10},
        "itinerary": [{"day": 1, "title": "Day one", "highlights": list(highlights)}],
        "tours": tours
    })


@pytest.fixture
def catalog() -> Catalog:
    trips = (
        trip(1, "Japan Express", "Japan", "Asia", 10, ["Art & Culture"],
             {"culture": 90, "party": 30}, "LOW", "Tokyo temples and Kyoto gardens",
             [tour(1, 1, "2027-03-01", "2027-03-10", 1500),
              tour(1, 2, "2027-04-01", "2027-04-10", 1300, status="NOT_AVAILABLE", seats=0)],
             highlights=["Cooking class in Kyoto"]),
        trip(2, "Thailand Beaches", "Thailand", None, 9, ["Beach Life", "Relax & Wellbeing"],
             {"relax": 90, "party": 70}, "LOW", "Island hopping and snorkelling",
             [tour(2, 1, "2027-02-05", "2027-02-13", 900, status="ALMOST_FULL", seats=2, age="18-25"),
              tour(2, 2, "2027-06-01", "2027-06-09", 1100)]),
        trip(3, "Iceland Northern Lights", "Iceland", "Europe", 7, ["Northern Lights"],
             {"nature": 95}, "MEDIUM", "Glacier walks and a volcano",
             [tour(3, 1, "2027-01-01", "2027-01-07", 1600),
              tour(3, 2, "2027-01-20", "2027-01-26", 1800)]),
        trip(4, "Peru Inca Trail", "Peru", "America", 14, ["Trekking & Hiking"],
             {"history": 80, "nature": 80}, "HIGH", "Trek to Machu Picchu",
             [tour(4, 1, "2027-05-01", "2027-05-14", 1700, status="PLANNED")]),
        trip(5, "Morocco Desert", "Morocco", None, 8, ["Standard"],
             {"culture": 70}, "MEDIUM", "Camel ride in the Sahara desert",
             [tour(5, 1, "2027-03-10", "2027-03-17", 800)])
    )
    faqs = (
        Faq(1, None, "Do I need a visa?", "Visa rules depend on your passport.", ""),
        Faq(2, "Japan", "Visa for Japan", "Most EU passports get a visa on arrival in Japan.", ""),
        Faq(3, "Peru", "Visa for Peru", "No visa needed for short stays in Peru.", "")
    )
    return Catalog(trips=trips, faqs=faqs)


def titles(results) -> set[str]:
    return {r.title for r in results}
