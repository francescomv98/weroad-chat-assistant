from app.models import SearchState
from app.service import search
from tests.conftest import TODAY, titles


def test_no_suggestions_when_there_are_results(catalog):
    resp = search(SearchState(continents=["Asia"]), catalog, TODAY)
    assert resp.total == 2
    assert resp.relaxations == []


def test_cheapest_change_comes_first(catalog):
    state = SearchState(continents=["Asia"], max_price=700)
    resp = search(state, catalog, TODAY)

    assert resp.total == 0

    first = resp.relaxations[0]
    
    assert first.relaxed_fields == ["max_price"]
    assert first.state.max_price == 910
    assert first.result_count == 1
    assert titles(resp.closest) == {"Thailand Beaches"}
    assert state.max_price == 700


def test_one_suggestion_per_field(catalog):
    resp = search(SearchState(continents=["Asia"], max_price=700), catalog, TODAY)
    fields = [r.relaxed_fields[0] for r in resp.relaxations]
    assert len(fields) == len(set(fields))


def test_destination_widens_to_its_continent_before_being_dropped(catalog):
    resp = search(SearchState(destinations=["Japan"], must_have=["snorkelling"]), catalog, TODAY)

    descriptions = [r.description for r in resp.relaxations]
    assert descriptions == ['drop "snorkelling"', "other destinations in Asia"]
    widened = resp.relaxations[1].state
    assert widened.destinations == [] and widened.continents == ["Asia"]


def test_combines_changes_when_no_single_one_is_enough(catalog):
    state = SearchState(continents=["Europe"], travel_types=["Beach Life"], physical_ratings=["HIGH"])
    resp = search(state, catalog, TODAY)

    assert len(resp.relaxations) == 1
    combo = resp.relaxations[0]
    assert set(combo.relaxed_fields) == {"travel_types", "physical_ratings"}
    assert combo.state.continents == ["Europe"]  
    assert titles(resp.closest) == {"Iceland Northern Lights"}
