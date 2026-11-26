"""End to end on the real sample data: unbookable departures never reach the page, suggestions
return what they promise, a conversation over several turns."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app import assistant as assistant_module
from app import config, main
from app.assistant import Assistant
from app.config import Settings
from app.data import BOOKABLE_STATUSES, get_catalog
from tests.test_assistant import FakeLLM, answer, call

FROZEN_TODAY = date(2026, 11, 24)

ZERO_RESULT_SEARCHES = [
    {"text": "northern lights", "max_price": 800},
    {"destinations": ["Japan"], "max_price": 900},
    {"must_have": ["cooking"], "date_from": "2027-10-19", "date_to": "2027-10-24"}
]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "settings", Settings(fixed_today=FROZEN_TODAY.isoformat()))
    monkeypatch.setattr(assistant_module, "settings", Settings(turn_log_path=str(tmp_path / "turns.jsonl")))
    return TestClient(main.app)


def assert_bookable(trips):
    for trip in trips:
        for dep in trip["departures"]:
            assert dep["status"] in BOOKABLE_STATUSES, (trip["title"], dep)
            assert dep["seats_left"] > 0, (trip["title"], dep)
            assert date.fromisoformat(dep["start"]) >= FROZEN_TODAY, (trip["title"], dep)


def test_sample_data_really_contains_unbookable_departures():
    statuses = {d.status for t in get_catalog().trips for d in t.departures}
    assert {"SOLD_OUT", "WAITING_LIST", "NOT_AVAILABLE"} <= statuses


@pytest.mark.parametrize("search", [{}, {"continents": ["Asia"]}, *ZERO_RESULT_SEARCHES])
def test_unbookable_departures_never_reach_the_page(client, search):
    body = client.post("/api/search", json=search).json()
    assert_bookable(body["results"])
    assert_bookable(body["closest"])


@pytest.mark.parametrize("search", ZERO_RESULT_SEARCHES)
def test_suggestions_deliver_what_they_promise(client, search):
    body = client.post("/api/search", json=search).json()
    assert body["total"] == 0
    assert body["relaxations"], "a zero-result search must never be a dead end"

    for suggestion in body["relaxations"]:
        followed = client.post("/api/search", json=suggestion["state"]).json()
        assert followed["total"] == suggestion["result_count"] > 0, suggestion["description"]

    first = client.post("/api/search", json=body["relaxations"][0]["state"]).json()
    assert [t["trip_id"] for t in body["closest"]] == [t["trip_id"] for t in first["results"]][:6]


def test_conversation_over_several_turns(client, monkeypatch):
    llm = FakeLLM(
        call("update_search", {"must_have": ["cooking"], "clear": ["text"]}),
        answer("Here are the trips with a cooking class."),
        call("update_search", {"date_from": "2027-10-19", "date_to": "2027-10-24"}),
        answer("Nothing on those days, but here's what's closest."),
        answer("Sure, what are you looking for?")
    )
    monkeypatch.setattr(main, "_assistant", Assistant(llm=llm, catalog=get_catalog(), today=FROZEN_TODAY))

    first = client.post("/api/chat", json={
        "message": "only trips with a cooking class",
        "state": {"text": "cooking class"}
    }).json()

    session = first["session_id"]
    assert first["search"]["state"]["must_have"] == ["cooking"]
    assert first["search"]["state"]["text"] is None
    assert first["search"]["total"] > 0

    second = client.post("/api/chat", json={
        "message": "I only have 19-24 October",
        "state": first["search"]["state"],
        "session_id": session
    }).json()

    state = second["search"]["state"]
    assert second["session_id"] == session
    assert state["must_have"] == ["cooking"]
    assert (state["date_from"], state["date_to"]) == ("2027-10-19", "2027-10-24")
    assert second["search"]["total"] == 0
    assert second["search"]["relaxations"]

    seen = llm.seen[-1]
    assert seen[0]["content"].endswith("only trips with a cooking class")
    assert '"must_have":["cooking"]' in seen[-3]["content"]

    assert client.post(f"/api/chat/{session}/reset").json() == {"ok": True}
    client.post("/api/chat", json={"message": "hello again", "session_id": session})
    assert [m["role"] for m in llm.seen[-1]] == ["user"]
