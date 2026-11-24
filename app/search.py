from __future__ import annotations
import re
from datetime import date
from .data import Catalog, Departure, Trip
from .models import DepartureOut, SearchState, TripResult

STOPWORDS = {
    "a", "an", "and", "the", "to", "in", "on", "of", "for", "with", "at", "by", "from", "or",
    "i", "me", "my", "we", "us", "our", "want", "would", "like", "looking", "trip", "trips",
    "travel", "tour", "tours", "holiday", "holidays", "vacation", "some", "something", "somewhere",
    "go", "going", "visit", "see", "please", "is", "are", "be", "that", "this", "it", "days", "day"
}

MAX_DEPARTURES_PER_TRIP = 5


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zà-ÿ0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def stem(word: str) -> str:
    """Very small English stemmer: good enough for 'beaches'→'beach', 'hiking'→'hik'."""
    for suffix in ("ies", "es", "ing", "s"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def _term_in_blob(term: str, blob: str) -> bool:
    return re.search(r"\b" + re.escape(stem(term)), blob) is not None


def text_score(query: str, trip: Trip) -> tuple[float, list[str]]:
    """Fraction of meaningful query terms found in the trip text (0..1)."""
    terms = tokenize(query)
    if not terms:
        return 1.0, []
    matched = [t for t in terms if _term_in_blob(t, trip.search_blob)]
    return len(matched) / len(terms), matched


def phrase_matches(phrase: str, trip: Trip) -> bool:
    terms = tokenize(phrase)
    return bool(terms) and all(_term_in_blob(t, trip.search_blob) for t in terms)


def _ci_in(value: str, options: list[str]) -> bool:
    return value.lower() in {o.lower() for o in options}


def trip_matches(trip: Trip, state: SearchState) -> bool:
    if state.continents and not _ci_in(trip.continent, state.continents):
        return False
    if state.destinations and not _ci_in(trip.destination, state.destinations):
        return False
    if state.travel_types and not any(_ci_in(tt, state.travel_types) for tt in trip.travel_types):
        return False
    if state.min_days and trip.days < state.min_days:
        return False
    if state.max_days and trip.days > state.max_days:
        return False
    if state.physical_ratings and trip.physical_rating not in state.physical_ratings:
        return False
    for mood, minimum in state.moods.active().items():
        if trip.moods.get(mood, 0) < minimum:
            return False
    if not all(phrase_matches(p, trip) for p in state.must_have):
        return False
    return True


def departure_matches(dep: Departure, state: SearchState, today: date) -> bool:
    if not dep.is_bookable(today):
        return False
    if state.date_from and dep.start < state.date_from:
        return False
    if state.date_to and dep.end > state.date_to:
        return False
    if state.max_price and dep.price_eur > state.max_price:
        return False
    if state.age_bands and dep.age_band not in state.age_bands:
        return False
    return True


def _to_result(trip: Trip, deps: list[Departure], score: float, matched: list[str]) -> TripResult:
    deps = sorted(deps, key=lambda d: d.start)

    return TripResult(
        trip_id=trip.id,
        title=trip.title,
        destination=trip.destination,
        continent=trip.continent,
        days=trip.days,
        url=trip.url,
        rating=trip.rating,
        short_description=trip.short_description,
        travel_types=list(trip.travel_types),
        from_price_eur=min(d.price_eur for d in deps),
        departures=[
            DepartureOut(
                id=d.id,
                start=d.start,
                end=d.end,
                price_eur=d.price_eur,
                base_price_eur=d.base_price_eur,
                status=d.status,
                seats_left=d.seats_left,
                age_band=d.age_band
            )
            for d in deps[:MAX_DEPARTURES_PER_TRIP]
        ],
        score=round(score, 3),
        matched_terms=matched
    )


def _sort(results: list[TripResult], sort: str) -> list[TripResult]:
    if sort == "price":
        return sorted(results, key=lambda r: r.from_price_eur)
    if sort == "date":
        return sorted(results, key=lambda r: r.departures[0].start)
    if sort == "rating":
        return sorted(results, key=lambda r: -(r.rating or 0))
    return sorted(results, key=lambda r: (-r.score, -(r.rating or 0)))


def run_search(catalog: Catalog, state: SearchState, today: date) -> list[TripResult]:
    """Exact search: every constraint in `state` is a hard filter.

    Free text is a filter too: with text_match="all" every meaningful word must
    match, which mirrors the current search page and is what produces many
    zero-result searches; "any" keeps trips matching at least one word.
    """
    results = []
    for trip in catalog.trips:
        if not trip_matches(trip, state):
            continue
        score, matched = text_score(state.text, trip) if state.text else (1.0, [])
        if state.text and (score == 0 or (state.text_match == "all" and score < 1)):
            continue
        deps = [d for d in trip.departures if departure_matches(d, state, today)]
        if not deps:
            continue
        results.append(_to_result(trip, deps, score, matched))
        
    return _sort(results, state.sort)
