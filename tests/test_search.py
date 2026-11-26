"""The exact search: text matching, date and price filters, moods, must-haves, sorting, and
sold-out departures never shown."""
from datetime import date

from app.models import Moods, SearchState
from app.search import run_search, text_score
from tests.conftest import TODAY, titles


def search(catalog, **filters):
    return run_search(catalog, SearchState(**filters), TODAY)


def test_text_search_ignores_filler_words_and_plurals(catalog):
    thailand = catalog.trip(2)
    score, matched = text_score("I'd like some islands trip", thailand)
    assert score == 1.0
    assert matched == ["islands"]


def test_all_words_must_match_unless_any_is_asked(catalog):
    assert search(catalog, text="snorkelling volcano") == []
    assert titles(search(catalog, text="snorkelling volcano", text_match="any")) == {
        "Thailand Beaches", "Iceland Northern Lights"
    }


def test_sold_out_and_already_started_departures_are_never_shown(catalog):
    by_title = {r.title: r for r in search(catalog)}
    assert [d.id for d in by_title["Japan Express"].departures] == ["1-1"]
    assert [d.id for d in by_title["Iceland Northern Lights"].departures] == ["3-2"]


def test_dates_must_contain_the_whole_trip(catalog):
    assert "Thailand Beaches" not in titles(search(catalog, date_from=date(2027, 2, 1), date_to=date(2027, 2, 12)))
    assert "Thailand Beaches" in titles(search(catalog, date_from=date(2027, 2, 1), date_to=date(2027, 2, 13)))


def test_dates_must_contain_the_whole_trip_and_must_be_available(catalog):
    assert "Japan Express" not in titles(search(catalog, date_from=date(2027, 4, 1), date_to=date(2027, 4, 10)))
    assert "Japan Express" in titles(search(catalog, date_from=date(2027, 2, 28), date_to=date(2027, 3, 13)))


def test_price_filter_keeps_only_cheap_departures(catalog):
    results = {r.title: r for r in search(catalog, max_price=1000)}
    assert set(results) == {"Thailand Beaches", "Morocco Desert"}
    assert [d.price_eur for d in results["Thailand Beaches"].departures] == [900]


def test_missing_continent_is_filled_from_destination(catalog):
    assert titles(search(catalog, continents=["asia"])) == {"Japan Express", "Thailand Beaches"}


def test_moods_are_minimum_scores(catalog):
    assert titles(search(catalog, moods=Moods(party=60))) == {"Thailand Beaches"}


def test_must_have_looks_inside_the_itinerary(catalog):
    assert titles(search(catalog, must_have=["cooking"])) == {"Japan Express"}


def test_sort_by_price_uses_cheapest_departure(catalog):
    results = search(catalog, sort="price")
    assert [r.title for r in results][:2] == ["Morocco Desert", "Thailand Beaches"]
