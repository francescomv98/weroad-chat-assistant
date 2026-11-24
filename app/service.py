from __future__ import annotations
from datetime import date
from .data import Catalog, get_catalog
from .models import SearchResponse, SearchState
from .relax import find_relaxations
from .search import run_search

def search(state: SearchState, catalog: Catalog | None = None, on: date | None = None) -> SearchResponse:
    catalog = catalog or get_catalog()
    on = on or date.today()
    results = run_search(catalog, state, on)
    
    if results:
        return SearchResponse(state=state, total=len(results), results=results)
    
    relaxations = find_relaxations(catalog, state, on)
    closest = run_search(catalog, relaxations[0].state, on)[:6] if relaxations else []
    
    return SearchResponse(state=state, total=0, results=[], relaxations=relaxations, closest=closest)
