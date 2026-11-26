from types import SimpleNamespace as NS

import pytest
from anthropic.types import Message

from app import llm
from app.config import Settings
from app.llm import (
    AnthropicClient,
    OpenAIClient,
    ToolCall,
    estimate_cost_usd,
    make_client,
    to_anthropic_messages,
)


def completion(content=None, tool_calls=None, finish="stop", prompt=1000, cached=0, out=50):
    msg = NS(content=content, tool_calls=tool_calls, refusal=None)
    usage = NS(prompt_tokens=prompt, completion_tokens=out, prompt_tokens_details=NS(cached_tokens=cached))
    return NS(choices=[NS(message=msg, finish_reason=finish)], usage=usage)


def fn_call(args):
    return NS(id="c1", type="function", function=NS(name="update_search", arguments=args))


def test_cached_tokens_are_billed_at_the_cheaper_rate():
    usage = {"input_tokens": 1_000_000, "cached_input_tokens": 1_000_000, "output_tokens": 1_000_000}
    assert estimate_cost_usd("gpt-4.1-mini", usage) == 2.10
    assert estimate_cost_usd("some-unknown-model", usage) is None


def test_cached_tokens_are_not_counted_twice():
    resp = OpenAIClient._parse(completion(content="hi", prompt=1000, cached=800))
    assert resp.usage == {"input_tokens": 200, "cached_input_tokens": 800, "output_tokens": 50}


def test_broken_tool_arguments_dont_raise():
    resp = OpenAIClient._parse(completion(tool_calls=[fn_call('{"max_price": 10')], finish="tool_calls"))
    assert resp.stop == "tool_use"
    assert resp.tool_calls[0].arguments is None
    assert resp.tool_calls[0].raw_arguments == '{"max_price": 10'


def test_cut_off_output_is_reported_as_max_tokens():
    resp = OpenAIClient._parse(completion(tool_calls=[fn_call('{"max')], finish="length"))
    assert resp.stop == "max_tokens"


def test_the_prompt_cache_key_is_sent_only_when_set():
    sent = []
    fake = NS(chat=NS(completions=NS(create=lambda **kw: sent.append(kw) or completion(content="hi"))))
    client = OpenAIClient(model="gpt-4.1-mini", reasoning_effort="")
    client._client = fake

    client.prompt_cache_key = "weroad-search-assistant"
    client.create(system="s", messages=[], tools=[])
    client.prompt_cache_key = ""
    client.create(system="s", messages=[], tools=[])

    assert sent[0]["prompt_cache_key"] == "weroad-search-assistant"
    assert "prompt_cache_key" not in sent[1]


# Anthropic


def claude_message(content, stop="end_turn", cache_read=0, cache_write=0):
    return Message.model_validate({
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": content, "stop_reason": stop, "stop_sequence": None,
        "usage": {"input_tokens": 100, "output_tokens": 20,
                  "cache_read_input_tokens": cache_read, "cache_creation_input_tokens": cache_write},
    })


def test_a_reply_with_thinking_and_a_tool_call_is_parsed_and_kept_whole():
    resp = AnthropicClient._parse(claude_message([
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "text", "text": "Let me search."},
        {"type": "tool_use", "id": "tu_1", "name": "update_search", "input": {"continents": ["Asia"]}},
    ], stop="tool_use", cache_read=1500, cache_write=300))

    assert resp.text == "Let me search." and resp.stop == "tool_use"
    assert resp.tool_calls[0].name == "update_search" and resp.tool_calls[0].arguments == {"continents": ["Asia"]}
    assert resp.usage == {"input_tokens": 100, "cached_input_tokens": 1500, "cache_write_input_tokens": 300, "output_tokens": 20}
    # The thinking block must be replayed unchanged in the next request.
    assert resp.raw_content["blocks"][0] == {"type": "thinking", "thinking": "", "signature": "sig"}


def test_a_refusal_is_reported_as_such():
    assert AnthropicClient._parse(claude_message([], stop="refusal")).stop == "refusal"


def test_the_history_is_converted_to_the_messages_api():
    call = ToolCall(id="tu_1", name="update_search", arguments={"max_price": 900})
    raw = {"provider": "anthropic", "blocks": [{"type": "thinking", "thinking": "", "signature": "sig"},
                                               {"type": "tool_use", "id": "tu_2", "name": "get_trip_details", "input": {"trip_id": 1}}]}
    history = [
        {"role": "user", "content": "Japan under 900"},
        {"role": "assistant", "content": "", "tool_calls": [call], "provider_content": None},
        {"role": "tool", "tool_call_id": "tu_1", "content": '{"result_count": 0}', "is_error": False},
        {"role": "assistant", "content": "", "tool_calls": [], "provider_content": raw},
        {"role": "tool", "tool_call_id": "tu_2", "content": '{"error": "x"}', "is_error": True},
    ]

    out = to_anthropic_messages(history)

    assert out[1] == {"role": "assistant", "content": [{"type": "tool_use", "id": "tu_1", "name": "update_search", "input": {"max_price": 900}}]}
    assert out[2] == {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "tu_1", "content": '{"result_count": 0}'}]}
    assert out[3] == {"role": "assistant", "content": raw["blocks"]}  # replayed as it came, thinking included
    assert out[4]["content"][0]["is_error"] is True


def test_the_request_caches_the_prompt_and_uses_fallbacks_only_where_supported():
    sent = []

    def create(**kw):
        sent.append(kw)
        return claude_message([{"type": "text", "text": "hi"}])

    fake = NS(messages=NS(create=create), beta=NS(messages=NS(create=create)))

    haiku = AnthropicClient(model="claude-haiku-5-5", effort="low")
    haiku._client = fake
    haiku.create(system="s", messages=[{"role": "user", "content": "hi"}], tools=[])
    opus = AnthropicClient(model="claude-opus-5-5", effort="")
    opus._client = fake
    opus.create(system="s", messages=[{"role": "user", "content": "hi"}], tools=[])

    assert sent[0]["cache_control"] == {"type": "ephemeral"} and sent[0]["output_config"] == {"effort": "low"}
    assert "fallbacks" not in sent[0]
    assert sent[1]["fallbacks"] == "default" and "output_config" not in sent[1]


def test_cache_writes_are_billed_at_one_and_a_quarter_times_input():
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "cache_write_input_tokens": 1_000_000}
    assert estimate_cost_usd("claude-opus-5-5", usage) == 5.0


def test_the_provider_comes_from_settings(monkeypatch):
    monkeypatch.setattr(llm, "settings", Settings(llm_provider="anthropic"))
    assert isinstance(make_client(), AnthropicClient)
    monkeypatch.setattr(llm, "settings", Settings(llm_provider="openai"))
    assert isinstance(make_client(), llm.OpenAIClient)
    monkeypatch.setattr(llm, "settings", Settings(llm_provider="mistral"))
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        make_client()


def test_both_providers_use_the_chat_timeout_and_keep_the_sdk_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(llm, "settings", Settings(llm_timeout_s=30))
    for client in (OpenAIClient()._get_client(), AnthropicClient()._get_client()):
        assert client.timeout == 30
        assert client.max_retries == 2


def test_the_fake_client_searches_then_replies_without_calling_any_api(catalog, tmp_path, monkeypatch):
    from app import assistant as assistant_module
    from app.assistant import Assistant
    from app.models import SearchState
    from tests.conftest import TODAY
    monkeypatch.setattr(assistant_module, "settings", Settings(turn_log_path=str(tmp_path / "t.jsonl")))
    monkeypatch.setattr(llm, "settings", Settings(llm_provider="fake", fake_llm_latency_s=0))
    bot = Assistant(llm=make_client(), catalog=catalog, today=TODAY)

    turn = bot.chat("anything", SearchState())

    assert turn.meta["tool_calls"] == ["update_search"]
    assert turn.search.state.continents == ["Asia"]
    assert turn.reply == "Here are some trips for you."
