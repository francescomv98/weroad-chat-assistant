"""Tracing with the real Langfuse SDK, exporting to memory instead of the network."""
import json
from types import SimpleNamespace as NS
import uuid
import pytest
from langfuse import Langfuse
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from app import assistant as assistant_module
from app import tracing
from app.assistant import Assistant
from app.config import Settings
from app.llm import LLMProviderError
from app.models import SearchState
from tests.conftest import TODAY
from tests.test_assistant import FakeLLM, answer, call


@pytest.fixture
def spans(monkeypatch, tmp_path):
    """Traces the test sends, as {name: attributes}, read after the turn."""
    monkeypatch.setattr(assistant_module, "settings", Settings(turn_log_path=str(tmp_path / "turns.jsonl")))
    exporter = InMemorySpanExporter()
    # A new public key each time: the SDK keeps one client per key.
    client = Langfuse(public_key=f"pk-lf-{uuid.uuid4().hex}", secret_key="sk-lf-test", base_url="http://localhost:9",
                      span_exporter=exporter, environment="test")
    tracing.configure(client=client)

    def read() -> dict[str, dict]:
        client.flush()
        return {s.name: dict(s.attributes) for s in exporter.get_finished_spans()}

    yield read
    client.shutdown()


def attr(span: dict, key: str):
    value = span.get(f"langfuse.observation.{key}")
    return json.loads(value) if isinstance(value, str) and value[:1] in "[{" else value


def test_a_turn_is_one_trace_with_the_llm_calls_and_the_tool_call(catalog, spans):
    llm = FakeLLM(call("update_search", {"continents": ["Asia"]}), answer("Try Thailand!"))
    bot = Assistant(llm=llm, catalog=catalog, today=TODAY)

    turn = bot.chat("Asia please", SearchState(), session_id="s-42")
    got = spans()

    assert set(got) == {"chat-turn", "llm-call-1", "llm-call-2", "update_search"}
    assert all(s["session.id"] == "s-42" for s in got.values())
    root = got["chat-turn"]
    assert attr(root, "type") == "agent" and attr(root, "input") == "Asia please" and attr(root, "output") == "Try Thailand!"
    assert attr(root, "metadata.result_count") == str(turn.search.total)
    assert json.loads(root["langfuse.trace.metadata.model"]) == "gpt-4.1-mini"

    first = got["llm-call-1"]
    assert attr(first, "type") == "generation" and attr(first, "model.name") == "gpt-4.1-mini"
    assert attr(first, "output")["tool_calls"] == [{"name": "update_search", "arguments": {"continents": ["Asia"]}}]
    assert attr(first, "usage_details") == {"input": 100, "output": 20}
    assert attr(first, "cost_details")["total"] > 0

    tool = got["update_search"]
    assert attr(tool, "type") == "tool" and attr(tool, "input") == {"continents": ["Asia"]}
    assert attr(tool, "output")["result_count"] == turn.search.total


def test_a_failed_tool_call_is_marked_as_an_error(catalog, spans):
    bot = Assistant(llm=FakeLLM(call("update_search", {"max_price": -5}), answer("Sorry")), catalog=catalog, today=TODAY)

    bot.chat("under -5 euros", SearchState())

    tool = spans()["update_search"]
    assert attr(tool, "level") == "ERROR"
    assert attr(tool, "output")["error"].startswith("invalid arguments")


def test_a_provider_error_is_recorded_and_the_turn_still_fails(catalog, spans):
    bot = Assistant(llm=FakeLLM(LLMProviderError(429, "busy")), catalog=catalog, today=TODAY)

    with pytest.raises(LLMProviderError):
        bot.chat("hi", SearchState())

    got = spans()
    assert attr(got["llm-call-1"], "level") == "ERROR" and attr(got["chat-turn"], "level") == "ERROR"


def test_tracing_is_on_only_with_both_keys(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    tracing.configure()
    assert not tracing.enabled()

    with tracing.turn("s", "hi", {}) as root:  # off: a no-op, nothing raises
        root.update(output="x")


def test_only_our_own_spans_are_exported(monkeypatch):
    """The Anthropic SDK traces its own calls with OpenTelemetry; those spans must not reach Langfuse."""
    import langfuse

    created = {}
    monkeypatch.setattr(langfuse, "Langfuse", lambda **kw: created.update(kw) or object())
    tracing.configure(enabled=True, environment="eval")

    assert created["should_export_span"] is langfuse.is_langfuse_span
    assert created["environment"] == "eval" and created["release"] == tracing.release()


def test_each_turn_returns_its_own_trace_id_and_the_context_ends_with_its_block(catalog, spans):
    bot = Assistant(llm=FakeLLM(answer("Hi!"), answer("Hi again!")), catalog=catalog, today=TODAY)

    with tracing.context(["eval-run:r1"], {"scenario": "hiking-lover"}):
        inside = bot.chat("hello", SearchState())
    outside = bot.chat("again", SearchState())

    assert inside.meta["trace_id"] and outside.meta["trace_id"] and inside.meta["trace_id"] != outside.meta["trace_id"]
    last_turn = spans()["chat-turn"]  # spans are keyed by name: this is the turn outside the context
    assert attr(last_turn, "output") == "Hi again!"
    assert list(last_turn["langfuse.trace.tags"]) == ["no-tools"]  # its outcome, none of the eval tags
    assert "langfuse.trace.metadata.scenario" not in last_turn


def test_eval_tags_and_metadata_reach_every_observation(catalog, spans):
    bot = Assistant(llm=FakeLLM(call("update_search", {"continents": ["Asia"]}), answer("ok")), catalog=catalog, today=TODAY)

    with tracing.context(["eval-run:r1"], {"scenario": "asia"}):
        bot.chat("Asia", SearchState())

    got = spans()
    for span in got.values():
        assert "eval-run:r1" in span["langfuse.trace.tags"]
        assert json.loads(span["langfuse.trace.metadata.scenario"]) == "asia"
    assert list(got["chat-turn"]["langfuse.trace.tags"]) == ["eval-run:r1", "outcome:results"]


def test_scores_are_sent_with_their_type(monkeypatch):
    sent = []
    client = NS(create_score=lambda **kw: sent.append(kw))
    tracing.configure(client=client)

    tracing.score("t1", "correct", False, "state: wrong")
    tracing.score("t1", "latency_s", 2.5)
    tracing.score(None, "correct", True)  # no trace (tracing was off for that turn): nothing to score

    assert sent == [
        {"trace_id": "t1", "name": "correct", "value": 0.0, "data_type": "BOOLEAN", "comment": "state: wrong"},
        {"trace_id": "t1", "name": "latency_s", "value": 2.5, "data_type": "NUMERIC", "comment": None},
    ]



@pytest.mark.parametrize("responses, expected", [
    ([call("update_search", {"continents": ["Asia"]}), answer("ok")], ["outcome:results"]),
    ([call("update_search", {"continents": ["Asia"], "max_price": 100}), answer("none")],
     ["outcome:zero-results-with-suggestions"]),
    ([call("get_faqs", {"faq_ids": [1]}), answer("Visa rules...")], ["faq"]),
    ([call("update_search", {"max_price": -5}), answer("sorry")], ["tool-error"]),
    ([answer("Where would you like to go?")], ["no-tools"]),
])
def test_the_turn_outcome_is_a_trace_tag(catalog, spans, responses, expected):
    bot = Assistant(llm=FakeLLM(*responses), catalog=catalog, today=TODAY, faq_retriever="index")

    bot.chat("something", SearchState())

    assert list(spans()["chat-turn"]["langfuse.trace.tags"]) == expected


def test_the_release_is_the_git_commit_unless_set(monkeypatch):
    monkeypatch.setenv("LANGFUSE_RELEASE", "v1.2")
    assert tracing.release() == "v1.2"

    monkeypatch.delenv("LANGFUSE_RELEASE")
    commit = tracing.release()
    assert commit and commit.split("-")[0].isalnum()  # e.g. "46696a0" or "46696a0-dirty"
