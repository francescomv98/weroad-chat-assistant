from types import SimpleNamespace as NS
from app.llm import OpenAIClient, estimate_cost_usd


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
