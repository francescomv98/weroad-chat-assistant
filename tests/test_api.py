from datetime import date
import pytest
from fastapi.testclient import TestClient
from app import config, main
from app.assistant import Assistant
from app.data import get_catalog
from app.llm import LLMProviderError
from tests.conftest import TODAY
from app.config import Settings
from tests.test_integration import FROZEN_TODAY


@pytest.fixture
def client():
    return TestClient(main.app)


def test_every_sample_trip_has_a_known_continent():
    assert "Other" not in get_catalog().continents


def test_empty_search_returns_bookable_trips(client, monkeypatch):
    monkeypatch.setattr(config, "settings", Settings(fixed_today=FROZEN_TODAY.isoformat()))
    body = client.post("/api/search", json={}).json()
    assert body["total"] == len(body["results"]) > 0


def test_impossible_ranges_are_rejected(client):
    res = client.post("/api/search", json={"date_from": "2027-05-01", "date_to": "2027-04-01"})
    assert res.status_code == 422
    res = client.post("/api/search", json={"min_days": 10, "max_days": 5})
    assert res.status_code == 422


def test_llm_errors_become_clean_http_errors(client, monkeypatch, catalog):
    class Busy:
        model = "gpt-4.1-mini"

        def create(self, **_):
            raise LLMProviderError(429, "The assistant is busy, please retry in a moment.")

    monkeypatch.setattr(main, "_assistant", Assistant(llm=Busy(), catalog=catalog, today=TODAY))

    res = client.post("/api/chat", json={"message": "hi"})

    assert res.status_code == 429
    assert res.json()["detail"] == "The assistant is busy, please retry in a moment."


@pytest.mark.parametrize("session_id", ["abc\nFAKE LOG LINE", "x" * 65, "../etc", ""])
def test_forged_session_ids_are_rejected(client, session_id):
    assert client.post("/api/chat", json={"message": "hi", "session_id": session_id}).status_code == 422


def test_bad_session_id_in_reset_is_rejected(client):
    assert client.post("/api/chat/bad%20id/reset").status_code == 422
    assert client.post("/api/chat/0123abcd/reset").status_code == 200


def test_home_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Trip Finder" in res.text


def test_fixed_today_is_used_by_the_whole_app(client, monkeypatch):
    """The page's date pickers (from /api/meta) and the bookable departures agree on the same day."""
    monkeypatch.setattr(config, "settings", Settings(fixed_today="2026-10-01"))
    early = client.post("/api/search", json={}).json()
    assert client.get("/api/meta").json()["today"] == "2026-10-01"

    monkeypatch.setattr(config, "settings", Settings(fixed_today="2027-06-01"))
    late = client.post("/api/search", json={}).json()

    starts = [d["start"] for r in late["results"] for d in r["departures"]]
    assert min(starts) >= "2027-06-01"
    assert early["total"] > late["total"]


def test_without_fixed_today_the_real_date_is_used(monkeypatch):
    monkeypatch.setattr(config, "settings", Settings(fixed_today=""))
    assert config.today() == date.today()


def test_a_wrong_fixed_today_fails_at_startup():
    with pytest.raises(ValueError, match="FIXED_TODAY"):
        Settings(fixed_today="24/11/2026")
