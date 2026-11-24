from __future__ import annotations
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from datetime import date
from pydantic import ValidationError
from . import service
from .config import settings
from .data import Catalog, get_catalog
from .llm import LLMClient, estimate_cost_usd, make_client
from .models import SearchResponse, SearchState
from .prompts import TOOLS, build_system_prompt
from .search import tokenize

log = logging.getLogger(__name__)

TOP_N_FOR_MODEL = 5


@dataclass
class Session:
    id: str
    messages: list[dict] = field(default_factory=list)


@dataclass
class TurnResult:
    session_id: str
    reply: str
    search: SearchResponse
    meta: dict[str, Any]


def _compact_trip(r) -> dict:
    return {
        "trip_id": r.trip_id,
        "title": r.title,
        "destination": r.destination,
        "days": r.days,
        "from_price_eur": r.from_price_eur,
        "rating": r.rating,
        "next_departures": [f"{d.start}→{d.end} €{d.price_eur} ({d.seats_left} seats)" for d in r.departures[:3]]
    }


def summarise_for_model(resp: SearchResponse) -> dict:
    """What the model sees after a search: small, factual, enough to talk about."""
    out: dict[str, Any] = {
        "result_count": resp.total,
        "active_filters": resp.state.describe(),
        "top_results": [_compact_trip(r) for r in resp.results[:TOP_N_FOR_MODEL]]
    }

    if resp.total == 0:
        out["relaxations"] = [
            {"change": r.description, "result_count": r.result_count, "new_filters": r.state.describe()}
            for r in resp.relaxations
        ]
        out["closest"] = [_compact_trip(r) for r in resp.closest[:TOP_N_FOR_MODEL]]

    return out


class Assistant:
    def __init__(self, llm: LLMClient | None = None, catalog: Catalog | None = None, today: date | None = None) -> None:
        self.catalog = catalog or get_catalog()
        self.llm = llm or make_client()
        self.today = today
        self.system = build_system_prompt(self.catalog)
        self.sessions: dict[str, Session] = {}

    # tools

    def _tool_update_search(self, state: SearchState, args: dict) -> tuple[SearchState, dict]:
        data = state.model_dump(mode="json")

        for f in args.pop("clear", None) or []:
            data[f] = SearchState.model_fields[f].get_default(call_default_factory=True)
            if f == "moods":
                data[f] = {}

        data.update(args)
        new_state = SearchState.model_validate(data)
        resp = service.search(new_state, self.catalog, date.today())

        return new_state, summarise_for_model(resp)

    def _tool_get_trip_details(self, trip_id: int) -> dict:
        trip = self.catalog.trip(trip_id)

        if not trip:
            return {"error": f"No trip with id {trip_id}"}
        
        return {
            "trip_id": trip.id,
            "title": trip.title,
            "destination": trip.destination,
            "days": trip.days,
            "physical_rating": trip.physical_rating,
            "moods": trip.moods,
            "travel_types": list(trip.travel_types),
            "rating": f"{trip.rating} ({trip.rating_count} reviews)" if trip.rating else "no reviews yet",
            "description": trip.description,
            "itinerary": [
                f"Day {d['day']}: {d['title']} - " + ", ".join(d.get("highlights") or []) for d in trip.itinerary
            ],
            "bookable_departures": [
                f"{d.start}→{d.end} €{d.price_eur} ({d.seats_left} seats, age {d.age_band})"
                for d in sorted(trip.departures, key=lambda d: d.start)
                if d.is_bookable(date.today())
            ],
            "url": trip.url
        }

    def _tool_search_faqs(self, query: str, destination: str | None = None) -> dict:
        terms = set(tokenize(query))
        scored = []

        for faq in self.catalog.faqs:
            if destination and faq.destination and faq.destination.lower() != destination.lower():
                continue
            words = set(tokenize(faq.title + " " + faq.body))
            score = len(terms & words) + (2 if destination and faq.destination else 0)
            if score:
                scored.append((score, faq))

        scored.sort(key=lambda x: -x[0])

        return {"faqs": [{"title": f.title, "answer": f.body, "url": f.url} for _, f in scored[:3]]}

    def _run_tool(self, name: str, args: dict, state: SearchState) -> tuple[SearchState, str, bool]:
        """Returns (possibly new state, result json, is_error)."""
        try:
            if name == "update_search":
                state, result = self._tool_update_search(state, dict(args))
            elif name == "get_trip_details":
                result = self._tool_get_trip_details(int(args["trip_id"]))
            elif name == "search_faqs":
                result = self._tool_search_faqs(args["query"], args.get("destination"))
            else:
                return state, json.dumps({"error": f"unknown tool {name}"}), True
            
        except (ValidationError, ValueError, KeyError, TypeError) as e:
            return state, json.dumps({"error": f"invalid arguments: {e}"}), True
        return state, json.dumps(result, default=str), False

    # turn loop

    def _context_block(self, state: SearchState) -> str:
        resp = service.search(state, self.catalog, date.today())

        return (
            "<context>\n"
            f"today: {date.today().isoformat()}\n"
            f"current_search: {state.model_dump_json(exclude_defaults=True)}\n"
            f"current_result_count: {resp.total}\n"
            "</context>\n\n"
        )

    def chat(self, message: str, state: SearchState, session_id: str | None = None) -> TurnResult:
        session = self.sessions.get(session_id or "") or Session(id=session_id or uuid.uuid4().hex)
        self.sessions[session.id] = session
        history_len = len(session.messages)

        try:
            return self._turn(session, message, state)
        except Exception:
            del session.messages[history_len:]
            raise

    def _turn(self, session: Session, message: str, state: SearchState) -> TurnResult:
        messages = session.messages
        messages.append({"role": "user", "content": self._context_block(state) + message})

        started = time.perf_counter()
        usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
        tool_calls: list[str] = []
        reply = ""

        for _round in range(settings.max_tool_rounds):
            response = self.llm.create(system=self.system, messages=messages, tools=TOOLS)
            for k in usage:
                usage[k] += response.usage.get(k, 0)

            if response.stop == "refusal":
                reply = "Sorry, I can't help with that. I can help you find a WeRoad trip, though!"
                messages.append({"role": "assistant", "content": reply, "tool_calls": []})
                break
            messages.append(
                {"role": "assistant", "content": response.text, "tool_calls": response.tool_calls}
            )
            if not response.tool_calls:
                reply = response.text.strip()
                break

            for call in response.tool_calls:
                tool_calls.append(call.name)
                if response.stop == "max_tokens":  
                    content, is_error = json.dumps({"error": "tool input was truncated, try again"}), True
                elif call.arguments is None:
                    content, is_error = json.dumps({"error": "arguments were not valid JSON", "received": call.raw_arguments}), True
                else:
                    state, content, is_error = self._run_tool(call.name, call.arguments, state)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": content, "is_error": is_error})
        else:
            reply = "I've updated the search - have a look at the results."

        search = service.search(state, self.catalog, date.today())
        meta = {
            "model": self.llm.model,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "tool_calls": tool_calls,
            "usage": usage,
            "cost_usd": estimate_cost_usd(self.llm.model, usage)
        }
        self._log_turn(session.id, message, reply, state, search.total, meta)
        
        return TurnResult(session_id=session.id, reply=reply, search=search, meta=meta)

    def reset(self, session_id: str) -> None:
        self.sessions.pop(session_id, None)

    @staticmethod
    def _log_turn(session_id: str, message: str, reply: str, state: SearchState, total: int, meta: dict) -> None:
        try:
            path = Path(settings.turn_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": time.time(),
                "session_id": session_id,
                "message": message,
                "reply": reply,
                "state": state.model_dump(mode="json", exclude_defaults=True),
                "result_count": total,
                **meta
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            log.exception("could not write turn log")