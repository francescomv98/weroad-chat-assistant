"""The in-memory session store: expiry, the cap with least recently used first, parallel saves,
and failed turns that store nothing."""
import threading

import pytest

from app.assistant import Assistant
from app.llm import LLMProviderError
from app.models import SearchState
from app.sessions import MemorySessionStore, Session
from tests.conftest import TODAY
from tests.test_assistant import FakeLLM, answer


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def store(ttl=60, max_sessions=3):
    clock = Clock()
    return MemorySessionStore(ttl_s=ttl, max_sessions=max_sessions, clock=clock), clock


def test_a_saved_session_comes_back():
    sessions, _ = store()
    sessions.save(Session("a", [{"role": "user", "content": "hi"}]))
    assert sessions.get("a").messages == [{"role": "user", "content": "hi"}]
    assert sessions.get("unknown") is None


def test_an_idle_session_expires_and_a_new_message_keeps_it_alive():
    sessions, clock = store(ttl=60)
    sessions.save(Session("a"))
    sessions.save(Session("b"))

    clock.now += 50
    sessions.save(sessions.get("b"))  # "b" gets a new message, "a" doesn't
    clock.now += 20  # "a" idle for 70 s, "b" for 20 s

    assert sessions.get("a") is None
    assert sessions.get("b") is not None
    assert len(sessions) == 1


def test_above_the_cap_the_least_recently_used_goes_first():
    sessions, clock = store(max_sessions=3)
    for sid in ("a", "b", "c"):
        sessions.save(Session(sid))
        clock.now += 1
    sessions.save(sessions.get("a"))  # "a" is now the most recent: "b" is the oldest

    sessions.save(Session("d"))

    assert [sid for sid in "abcd" if sessions.get(sid)] == ["a", "c", "d"]


def test_delete_forgets_a_session_and_ignores_unknown_ids():
    sessions, _ = store()
    sessions.save(Session("a"))
    sessions.delete("a")
    sessions.delete("never-existed")
    assert sessions.get("a") is None


def test_parallel_saves_keep_the_cap():
    sessions, _ = store(max_sessions=50)

    def save_many(prefix):
        for i in range(200):
            sessions.save(Session(f"{prefix}-{i}"))

    threads = [threading.Thread(target=save_many, args=(p,)) for p in "abcdefgh"]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(sessions) == 50


def test_an_expired_session_restarts_empty_under_the_same_id(catalog):
    sessions, clock = store(ttl=60)
    bot = Assistant(llm=FakeLLM(answer("Hi!"), answer("Hello again!")), catalog=catalog, today=TODAY, sessions=sessions)
    first = bot.chat("hello", SearchState())
    assert len(sessions.get(first.session_id).messages) == 2

    clock.now += 61
    second = bot.chat("still there?", SearchState(), first.session_id)

    assert second.session_id == first.session_id
    assert len(sessions.get(first.session_id).messages) == 2  # only the new turn


def test_a_failed_first_turn_stores_nothing(catalog):
    sessions, _ = store()
    bot = Assistant(llm=FakeLLM(LLMProviderError(429, "busy")), catalog=catalog, today=TODAY, sessions=sessions)

    with pytest.raises(LLMProviderError):
        bot.chat("hello", SearchState(), "s-1")

    assert sessions.get("s-1") is None
