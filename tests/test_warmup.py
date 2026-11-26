import logging
import threading
import time

from app import main
from app.assistant import Assistant
from app.config import Settings
from app.llm import LLMProviderError
from tests.conftest import TODAY
from tests.test_assistant import FakeLLM, fake_embed


class NoKeyLLM(FakeLLM):
    """A provider whose SDK client can't start (no API key), like a missing ANTHROPIC_API_KEY."""

    def _get_client(self):
        raise LLMProviderError(500, "No Anthropic credentials")


def test_the_warm_up_loads_the_faq_embeddings_and_survives_a_failing_step(catalog, monkeypatch, caplog):
    embedded = []

    def counting_embed(texts):
        embedded.append(len(texts))
        return fake_embed(texts)

    bot = Assistant(llm=NoKeyLLM(), catalog=catalog, today=TODAY, faq_retriever="embeddings", embed=counting_embed)
    monkeypatch.setattr(main, "_assistant", bot)
    caplog.set_level(logging.INFO, logger="uvicorn.error")

    main.warm_up()  # must not raise although the LLM client step fails

    assert embedded == [len(catalog.faqs)]  # the step after the failing one still ran
    assert any("LLM client failed" in r.getMessage() for r in caplog.records)
    assert any("warm-up done" in r.getMessage() for r in caplog.records)


def test_the_warm_up_and_the_first_request_build_one_assistant(monkeypatch):
    built = []

    class SlowAssistant:
        def __init__(self):
            time.sleep(0.05)  # long enough for the other threads to arrive while it's being built
            built.append(self)

    monkeypatch.setattr(main, "_assistant", None)
    monkeypatch.setattr(main, "Assistant", SlowAssistant)
    threads = [threading.Thread(target=main.get_assistant) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(built) == 1


def test_no_warm_up_when_it_is_turned_off(monkeypatch):
    from fastapi.testclient import TestClient

    called = []
    monkeypatch.setattr(main.config, "settings", Settings(warmup=False))
    monkeypatch.setattr(main, "warm_up", lambda: called.append(True))

    with TestClient(main.app):  # runs the startup
        pass

    assert called == []


def test_the_assistant_is_ready_after_the_warm_up_even_if_a_step_failed(catalog, monkeypatch):
    bot = Assistant(llm=NoKeyLLM(), catalog=catalog, today=TODAY, faq_retriever="embeddings", embed=fake_embed)
    monkeypatch.setattr(main, "_assistant", bot)
    main.assistant_ready.clear()

    main.warm_up()

    assert main.assistant_ready.is_set()


def test_meta_says_whether_the_assistant_is_ready(monkeypatch):
    from fastapi.testclient import TestClient

    client = TestClient(main.app)  # no `with`: the startup (and its warm-up) doesn't run
    main.assistant_ready.clear()
    assert client.get("/api/meta").json()["assistant_ready"] is False
    main.assistant_ready.set()
    assert client.get("/api/meta").json()["assistant_ready"] is True


def test_readiness_polls_are_kept_out_of_the_access_log():
    import logging as _logging

    def line(path):
        return _logging.LogRecord("uvicorn.access", _logging.INFO, "", 0, '%s - "GET %s HTTP/1.1" %d',
                                  ("127.0.0.1:1", path, 200), None)

    assert main._HideReadinessPolls().filter(line("/api/ready")) is False
    assert main._HideReadinessPolls().filter(line("/api/meta")) is True
    assert main.ready() == {"assistant_ready": main.assistant_ready.is_set()}
