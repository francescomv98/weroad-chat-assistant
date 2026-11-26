"""Invariants of search and relaxation, checked on many random searches over the real sample data.

The example tests in test_search.py / test_relax.py show the behaviour on hand-picked cases; these check
the promises the app makes for *any* search: never a sold-out or past departure, every result respects
every filter, zero results is never a dead end, every suggestion returns the count it announces.
The checks re-implement each filter on their own instead of calling trip_matches, or they would only
prove that the code agrees with itself. Seeded, so a failure always reproduces: the message has the state.
"""
from __future__ import annotations

import random
from datetime import timedelta

import pytest

from app.data import BOOKABLE_STATUSES, get_catalog
from app.models import Moods, SearchState
from app.search import run_search, stem, tokenize
from app.service import search
from tests.test_integration import FROZEN_TODAY

N_SEARCHES = 400

# Words that match many, few or no trips, so the random searches hit both results and zero results.
WORDS = ["beach", "temple", "hiking", "desert", "cooking", "safari", "volcano", "island", "food", "xyzzy"]

# Which SearchState fields each relaxation is allowed to change.
FIELDS_OF = {
    "text": {"text", "text_match"},
    "dates": {"date_from", "date_to"},
    "max_price": {"max_price"},
    "days": {"min_days", "max_days"},
    "must_have": {"must_have"},
    "moods": {"moods"},
    "travel_types": {"travel_types"},
    "physical_ratings": {"physical_ratings"},
    "age_bands": {"age_bands"},
    "destinations": {"destinations", "continents"},  # "other destinations in Asia" sets the continent
    "continents": {"continents"},
}


def maybe(rng: random.Random, value, p: float = 0.3):
    return value if rng.random() < p else None


def random_state(rng: random.Random, catalog) -> SearchState:
    min_days = maybe(rng, rng.randint(3, 12))
    max_days = maybe(rng, rng.randint(min_days or 3, 16))
    date_from = maybe(rng, FROZEN_TODAY + timedelta(days=rng.randint(-30, 300)))
    date_to = maybe(rng, (date_from or FROZEN_TODAY) + timedelta(days=rng.randint(3, 120)))
    moods = {m: rng.choice([30, 60, 90]) for m in ("party", "relax", "nature", "culture", "history") if rng.random() < 0.15}
    return SearchState(
        text=maybe(rng, " ".join(rng.sample(WORDS, rng.randint(1, 3))), 0.25),
        text_match=rng.choice(["all", "any"]),
        date_from=date_from,
        date_to=date_to,
        max_price=maybe(rng, rng.randint(3, 50) * 100),
        min_days=min_days,
        max_days=max_days,
        continents=rng.sample(catalog.continents, rng.randint(1, 2)) if rng.random() < 0.3 else [],
        destinations=rng.sample(catalog.destinations, rng.randint(1, 2)) if rng.random() < 0.2 else [],
        travel_types=rng.sample(catalog.travel_types, 1) if rng.random() < 0.2 else [],
        must_have=rng.sample(WORDS, 1) if rng.random() < 0.2 else [],
        moods=Moods(**moods),
        physical_ratings=rng.sample(["LOW", "MEDIUM", "HIGH"], rng.randint(1, 2)) if rng.random() < 0.2 else [],
        age_bands=rng.sample(["18-25", "25-35", "25-49"], 1) if rng.random() < 0.2 else [],
        sort=rng.choice(["relevance", "price", "date", "rating"]),
    )


def assert_result_respects(result, state: SearchState, catalog) -> None:
    trip = catalog.trip(result.trip_id)

    def lower(values):
        return {v.lower() for v in values}

    if state.continents:
        assert result.continent.lower() in lower(state.continents)
    if state.destinations:
        assert result.destination.lower() in lower(state.destinations)
    if state.travel_types:
        assert lower(result.travel_types) & lower(state.travel_types)
    if state.min_days:
        assert result.days >= state.min_days
    if state.max_days:
        assert result.days <= state.max_days
    if state.physical_ratings:
        assert trip.physical_rating in state.physical_ratings
    for mood, minimum in state.moods.active().items():
        assert trip.moods.get(mood, 0) >= minimum
    # Substring of the stem: weaker than the search's word-boundary match, but never wrongly fails.
    for phrase in state.must_have:
        assert all(stem(w) in trip.search_blob for w in tokenize(phrase))
    if state.text and state.text_match == "all":
        assert all(stem(w) in trip.search_blob for w in tokenize(state.text))
    if state.max_price:
        assert result.from_price_eur <= state.max_price
    assert result.departures, "a trip is shown only with at least one departure"
    for dep in result.departures:
        # The business rule: only bookable departures, whatever the search.
        assert dep.status in BOOKABLE_STATUSES and dep.seats_left > 0 and dep.start >= FROZEN_TODAY
        if state.date_from:
            assert dep.start >= state.date_from
        if state.date_to:
            assert dep.end <= state.date_to
        if state.max_price:
            assert dep.price_eur <= state.max_price
        if state.age_bands:
            assert dep.age_band in state.age_bands


def changed_fields(before: SearchState, after: SearchState) -> set[str]:
    a, b = before.model_dump(), after.model_dump()
    return {k for k in a if a[k] != b[k]}


@pytest.fixture(scope="module")
def searches():
    """N_SEARCHES random states and their responses, computed once for all the checks below."""
    catalog = get_catalog()
    rng = random.Random(20261125)
    out = []
    for _ in range(N_SEARCHES):
        state = random_state(rng, catalog)
        out.append((state, search(state, catalog, FROZEN_TODAY)))
    return catalog, out


def test_the_random_searches_cover_both_results_and_zero_results(searches):
    _, out = searches
    zero = sum(resp.total == 0 for _, resp in out)
    # Otherwise the relaxation invariants below would be checked on almost nothing.
    assert 0.2 * N_SEARCHES < zero < 0.8 * N_SEARCHES, zero


def test_every_result_is_bookable_and_respects_every_filter(searches):
    catalog, out = searches
    for state, resp in out:
        assert resp.total == len(resp.results)
        for result in resp.results:
            try:
                assert_result_respects(result, state, catalog)
            except AssertionError as e:
                raise AssertionError(f"{result.title} for {state.model_dump_json(exclude_defaults=True)}") from e


def test_results_follow_the_requested_order(searches):
    _, out = searches
    for state, resp in out:
        prices = [r.from_price_eur for r in resp.results]
        starts = [r.departures[0].start for r in resp.results]
        if state.sort == "price":
            assert prices == sorted(prices), state.model_dump_json(exclude_defaults=True)
        if state.sort == "date":
            assert starts == sorted(starts), state.model_dump_json(exclude_defaults=True)


def test_zero_results_is_never_a_dead_end(searches):
    _, out = searches
    for state, resp in out:
        if resp.total == 0:
            assert resp.relaxations and resp.closest, state.model_dump_json(exclude_defaults=True)
        else:
            assert not resp.relaxations and not resp.closest


def test_every_suggestion_returns_the_trips_it_announces(searches):
    catalog, out = searches
    for state, resp in out:
        for r in resp.relaxations:
            results = run_search(catalog, r.state, FROZEN_TODAY)
            assert r.result_count == len(results) > 0, (r.description, state.model_dump_json(exclude_defaults=True))
            for result in results:
                assert_result_respects(result, r.state, catalog)
        if resp.relaxations:
            # The closest trips are the first suggestion's results, so they are bookable too.
            first = run_search(catalog, resp.relaxations[0].state, FROZEN_TODAY)
            assert [c.trip_id for c in resp.closest] == [t.trip_id for t in first[:len(resp.closest)]]


def test_a_suggestion_only_changes_the_fields_it_names(searches):
    """The user's other filters stay as they are: "under 900" must not silently become "any budget"."""
    _, out = searches
    for state, resp in out:
        for r in resp.relaxations:
            allowed = set().union(*(FIELDS_OF[f] for f in r.relaxed_fields))
            assert changed_fields(state, r.state) <= allowed, (r.description, state.model_dump_json(exclude_defaults=True))


def test_single_suggestions_are_one_per_field_and_at_most_three(searches):
    _, out = searches
    for state, resp in out:
        assert len(resp.relaxations) <= 3
        fields = [r.relaxed_fields[0] for r in resp.relaxations if len(r.relaxed_fields) == 1]
        assert len(fields) == len(set(fields)), state.model_dump_json(exclude_defaults=True)


def test_a_suggestion_never_makes_the_search_stricter(searches):
    """Budget, dates and trip length only ever widen."""
    _, out = searches
    for state, resp in out:
        for r in resp.relaxations:
            s = r.state
            if state.max_price and s.max_price:
                assert s.max_price >= state.max_price
            if state.date_from and s.date_from:
                assert s.date_from <= state.date_from
            if state.date_to and s.date_to:
                assert s.date_to >= state.date_to
            if state.min_days and s.min_days:
                assert s.min_days <= state.min_days
            if state.max_days and s.max_days:
                assert s.max_days >= state.max_days
