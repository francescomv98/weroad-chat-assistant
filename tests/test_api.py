import pytest
from fastapi.testclient import TestClient
from app import main, service
from app.assistant import Assistant
from app.data import get_catalog
from app.llm import LLMProviderError
from tests.conftest import TODAY
from tests.test_integration import FrozenDate


@pytest.fixture
def client():
    return TestClient(main.app)


def test_every_sample_trip_has_a_known_continent():
    assert "Other" not in get_catalog().continents


def test_empty_search_returns_bookable_trips(client, monkeypatch):
    monkeypatch.setattr(service, "date", FrozenDate)
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


def test_home_page_is_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Trip Finder" in res.text
