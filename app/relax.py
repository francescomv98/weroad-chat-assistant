from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable
from .data import Catalog
from .models import Moods, Relaxation, SearchState
from .search import run_search, tokenize

MAX_SUGGESTIONS = 3


@dataclass
class _Step:
    field: str
    cost: int
    description: str
    apply: Callable[[SearchState], SearchState]


def _upd(**changes) -> Callable[[SearchState], SearchState]:
    return lambda s: s.model_copy(update=changes)


def _widen_dates(days: int) -> Callable[[SearchState], SearchState]:
    def apply(s: SearchState) -> SearchState:
        return s.model_copy(
            update={
                "date_from": s.date_from - timedelta(days=days) if s.date_from else None,
                "date_to": s.date_to + timedelta(days=days) if s.date_to else None,
            }
        )

    return apply


def candidate_steps(state: SearchState, catalog: Catalog) -> list[_Step]:
    steps: list[_Step] = []
    if state.text:
        if state.text_match == "all" and len(tokenize(state.text)) > 1:
            steps.append(_Step("text", 1, f'match any of the words in "{state.text}"', _upd(text_match="any")))
        steps.append(_Step("text", 2, f'ignore the free text "{state.text}"', _upd(text=None, text_match="all")))
    if state.date_from or state.date_to:
        for days, cost in ((7, 2), (14, 3), (30, 5)):
            steps.append(_Step("dates", cost, f"move dates by up to {days} days", _widen_dates(days)))
        steps.append(_Step("dates", 7, "any dates", _upd(date_from=None, date_to=None)))
    if state.max_price:
        for pct, cost in ((15, 2), (30, 4)):
            new = int(state.max_price * (1 + pct / 100))
            steps.append(_Step("max_price", cost, f"budget up to €{new} (+{pct}%)", _upd(max_price=new)))
        steps.append(_Step("max_price", 6, "no budget limit", _upd(max_price=None)))
    if state.min_days or state.max_days:
        steps.append(
            _Step(
                "days",
                2,
                "trip length ±2 days",
                _upd(
                    min_days=max(1, state.min_days - 2) if state.min_days else None,
                    max_days=state.max_days + 2 if state.max_days else None,
                ),
            )
        )
        steps.append(_Step("days", 5, "any trip length", _upd(min_days=None, max_days=None)))
    for phrase in state.must_have:
        remaining = [p for p in state.must_have if p != phrase]
        steps.append(_Step("must_have", 4, f'drop "{phrase}"', _upd(must_have=remaining)))
    if state.moods.active():
        steps.append(_Step("moods", 3, "ignore mood preferences", _upd(moods=Moods())))
    if state.travel_types:
        steps.append(_Step("travel_types", 3, "any travel type", _upd(travel_types=[])))
    if state.physical_ratings:
        steps.append(_Step("physical_ratings", 3, "any physical level", _upd(physical_ratings=[])))
    if state.age_bands:
        steps.append(_Step("age_bands", 3, "any age group", _upd(age_bands=[])))
    if state.destinations:
        dests = {d.lower() for d in state.destinations}
        continents = sorted({t.continent for t in catalog.trips if t.destination.lower() in dests})
        if continents:
            steps.append(
                _Step(
                    "destinations",
                    5,
                    f"other destinations in {', '.join(continents)}",
                    _upd(destinations=[], continents=continents)
                )
            )
        steps.append(_Step("destinations", 8, "any destination", _upd(destinations=[])))
    if state.continents:
        steps.append(_Step("continents", 6, "any continent", _upd(continents=[])))
    return steps


def find_relaxations(catalog: Catalog, state: SearchState, today: date) -> list[Relaxation]:
    steps = candidate_steps(state, catalog)

    # 1) Single-step relaxations, cheapest first; one suggestion per field.
    found: list[tuple[int, Relaxation]] = []
    seen_fields: set[str] = set()
    for step in sorted(steps, key=lambda s: s.cost):
        if step.field in seen_fields:
            continue
        relaxed = step.apply(state)
        count = len(run_search(catalog, relaxed, today))
        if count:
            seen_fields.add(step.field)
            found.append(
                (step.cost, Relaxation(description=step.description, relaxed_fields=[step.field], state=relaxed, result_count=count))
            )
    if found:
        found.sort(key=lambda x: (x[0], -x[1].result_count))
        return [r for _, r in found[:MAX_SUGGESTIONS]]

    # 2) Nothing works alone: clear whole fields one at a time (cheapest field first) and stop as soon as something comes back.
    strongest: dict[str, _Step] = {}
    for step in steps:
        if step.field not in strongest or step.cost > strongest[step.field].cost:
            strongest[step.field] = step
    if "must_have" in strongest: 
        strongest["must_have"] = _Step("must_have", 4, "drop the must-have activities", _upd(must_have=[]))
    current, descriptions, fields = state, [], []
    for step in sorted(strongest.values(), key=lambda s: s.cost):
        current = step.apply(current)
        descriptions.append(step.description)
        fields.append(step.field)
        count = len(run_search(catalog, current, today))
        if count:
            return [Relaxation(description="; ".join(descriptions), relaxed_fields=fields, state=current, result_count=count)]
    return []