from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol
from .config import settings

Stop = Literal["end", "tool_use", "max_tokens", "refusal"]


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] | None  
    raw_arguments: str = ""


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall]
    stop: Stop
    usage: dict[str, int] = field(default_factory=dict)  
    # The provider's own reply blocks, replayed unchanged in the next request when the provider needs it
    # (Claude's thinking blocks). None for OpenAI.
    raw_content: Any = None


class LLMProviderError(Exception):
    """Provider failure, mapped to an HTTP status the API can return."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class LLMClient(Protocol):
    model: str

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


# USD per million tokens: (input, cached input, output). Anthropic also bills cache writes at 1.25x input.
PRICES = {
    "claude-opus-5-5": (4.00, 0.20, 20.00),
    "claude-sonnet-5-5": (2.00, 0.10, 10.00),
    "claude-haiku-5-5": (0.10, 0.01, 0.50),
    "gpt-5": (1.25, 0.125, 10.00),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-4.1": (2.00, 0.50, 8.00),
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-4o-mini": (0.15, 0.075, 0.60)
}

EMBEDDING_PRICE_PER_M = 0.02  # text-embedding-3-small


def estimate_cost_usd(model: str, usage: dict[str, int]) -> float | None:
    price = PRICES.get(model)
    if not price:
        return None
    p_in, p_cached, p_out = price
    cost = (
        usage.get("input_tokens", 0) * p_in
        + usage.get("cached_input_tokens", 0) * p_cached
        + usage.get("output_tokens", 0) * p_out
        + usage.get("cache_write_input_tokens", 0) * p_in * 1.25
        + usage.get("embedding_tokens", 0) * EMBEDDING_PRICE_PER_M
    )
    return round(cost / 1_000_000, 6)


def _parse_args(raw: str) -> dict | None:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


# --------------------------------------------------------------------------- OpenAI

def to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for m in messages:
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": m.get("content") or None}
            if m.get("tool_calls"):
                msg["tool_calls"] = [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": tc.raw_arguments}}
                    for tc in m["tool_calls"]
                ]
            out.append(msg)
        elif m["role"] == "tool":
            out.append({"role": "tool", "tool_call_id": m["tool_call_id"], "content": m["content"]})
    return out


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["input_schema"]}}
        for t in tools
    ]


class OpenAIClient:
    provider = "openai"

    def __init__(self, model: str | None = None, reasoning_effort: str | None = None) -> None:
        self.model = model or settings.openai_model
        self.effort = reasoning_effort if reasoning_effort is not None else settings.openai_reasoning_effort
        self.prompt_cache_key = settings.openai_prompt_cache_key
        self._client = None

    def _get_client(self):
        import openai

        if self._client is None:
            try:
                self._client = openai.OpenAI(timeout=settings.llm_timeout_s)
            except openai.OpenAIError as e:
                raise LLMProviderError(500, "No OpenAI credentials: set OPENAI_API_KEY in .env") from e
        return self._client

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        import openai

        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=to_openai_messages(system, messages),
            tools=to_openai_tools(tools),
            max_completion_tokens=8000
        )
        if self.effort:  
            kwargs["reasoning_effort"] = self.effort
        if self.prompt_cache_key:
            kwargs["prompt_cache_key"] = self.prompt_cache_key
        try:
            completion = self._get_client().chat.completions.create(**kwargs)
        except openai.AuthenticationError as e:
            raise LLMProviderError(500, "OpenAI API key invalid: check OPENAI_API_KEY in .env") from e
        except openai.RateLimitError as e:
            raise LLMProviderError(429, "The assistant is busy, please retry in a moment.") from e
        except openai.APIConnectionError as e:
            raise LLMProviderError(502, "Could not reach OpenAI.") from e
        except openai.APIStatusError as e:
            raise LLMProviderError(502, f"OpenAI error: {e.message}") from e
        return self._parse(completion)

    @staticmethod
    def _parse(completion) -> LLMResponse:
        choice = completion.choices[0]
        msg = choice.message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=_parse_args(tc.function.arguments), raw_arguments=tc.function.arguments)
            for tc in (msg.tool_calls or [])
            if tc.type == "function"
        ]
        if msg.refusal or choice.finish_reason == "content_filter":
            stop: Stop = "refusal"
        elif choice.finish_reason == "length":
            stop = "max_tokens"
        elif tool_calls:
            stop = "tool_use"
        else:
            stop = "end"
        usage: dict[str, int] = {}
        if completion.usage:
            cached = getattr(completion.usage.prompt_tokens_details, "cached_tokens", 0) or 0
            usage = {
                "input_tokens": completion.usage.prompt_tokens - cached,
                "cached_input_tokens": cached,
                "output_tokens": completion.usage.completion_tokens
            }
        return LLMResponse(text=msg.content or "", tool_calls=tool_calls, stop=stop, usage=usage)


# --------------------------------------------------------------------------- Anthropic

# The assistant keeps one provider-neutral history (user / assistant + tool_calls / tool messages); this
# section converts it to Anthropic's Messages API format and back. Two Claude-specific points:
# - Current Claude models think before answering, and their thinking blocks must be sent back unchanged
#   in the tool loop. The raw content blocks of each reply travel in the history as `provider_content`
#   and are replayed as they are, instead of being rebuilt from the text and tool calls.
# - Prompt caching is explicit: `cache_control` marks the prompt for caching (tools -> system -> messages
#   is a stable prefix here, as with OpenAI).

ANTHROPIC = "anthropic"

# Models that support server-side refusal fallbacks: a request declined by the safety classifiers is
# re-run on a fallback model chosen by the API inside the same call.
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-opus-5", "claude-fable-5-2", "claude-fable-5-1"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_ANTHROPIC_STOPS: dict[str, Stop] = {"tool_use": "tool_use", "max_tokens": "max_tokens", "refusal": "refusal"}


def to_anthropic_messages(messages: list[dict]) -> list[dict]:
    """Provider-neutral history -> Messages API. Consecutive tool results go back in one user message."""
    out: list[dict] = []
    results: list[dict] = []

    def flush() -> None:
        if results:
            out.append({"role": "user", "content": list(results)})
            results.clear()

    for m in messages:
        if m["role"] == "tool":
            block = {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]}
            if m.get("is_error"):
                block["is_error"] = True
            results.append(block)
            continue
        flush()
        if m["role"] == "user":
            out.append({"role": "user", "content": m["content"]})
        elif m["role"] == "assistant":
            raw = m.get("provider_content")
            if raw and raw.get("provider") == ANTHROPIC:
                out.append({"role": "assistant", "content": raw["blocks"]})
                continue
            blocks: list[dict] = [{"type": "text", "text": m["content"]}] if m.get("content") else []
            blocks += [
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments or {}}
                for tc in m.get("tool_calls") or []
            ]
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
    flush()
    return out


class AnthropicClient:
    provider = "anthropic"

    def __init__(self, model: str | None = None, effort: str | None = None) -> None:
        self.model = model or settings.anthropic_model
        self.effort = effort if effort is not None else settings.anthropic_effort
        self._client = None

    def _get_client(self):
        import anthropic

        if self._client is None:
            try:
                self._client = anthropic.Anthropic(timeout=settings.llm_timeout_s)
            except anthropic.AnthropicError as e:
                raise LLMProviderError(500, "No Anthropic credentials: set ANTHROPIC_API_KEY in .env") from e
        return self._client

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        import anthropic

        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=16000,
            system=system,
            tools=tools,  
            messages=to_anthropic_messages(messages),
            cache_control={"type": "ephemeral"}
        )
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        try:
            client = self._get_client()
            if self.model in FALLBACK_MODELS:
                response = client.beta.messages.create(betas=[FALLBACK_BETA], fallbacks="default", **kwargs)
            else:
                response = client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise LLMProviderError(500, "Anthropic API key invalid: check ANTHROPIC_API_KEY in .env") from e
        except anthropic.RateLimitError as e:
            raise LLMProviderError(429, "The assistant is busy, please retry in a moment.") from e
        except anthropic.APIConnectionError as e:
            raise LLMProviderError(502, "Could not reach Anthropic.") from e
        except anthropic.APIStatusError as e:
            raise LLMProviderError(502, f"Anthropic error: {e.message}") from e
        return self._parse(response)

    @staticmethod
    def _parse(response) -> LLMResponse:
        text = "".join(b.text for b in response.content if b.type == "text")
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=b.input if isinstance(b.input, dict) else None,
                     raw_arguments=json.dumps(b.input))
            for b in response.content if b.type == "tool_use"
        ]
        u = response.usage
        usage = {
            "input_tokens": u.input_tokens,
            "cached_input_tokens": u.cache_read_input_tokens or 0,
            "cache_write_input_tokens": u.cache_creation_input_tokens or 0,
            "output_tokens": u.output_tokens
        }
        return LLMResponse(
            text=text, tool_calls=tool_calls, stop=_ANTHROPIC_STOPS.get(response.stop_reason, "end"), usage=usage,
            raw_content={"provider": ANTHROPIC, "blocks": [b.model_dump(mode="json", exclude_none=True) for b in response.content]}
        )


def make_client() -> LLMClient:
    """LLM_PROVIDER picks the provider: "anthropic" (default) or "openai"."""
    if settings.llm_provider == "anthropic":
        return AnthropicClient()
    if settings.llm_provider != "openai":
        raise ValueError(f"LLM_PROVIDER must be 'openai' or 'anthropic', got {settings.llm_provider!r}")
    return OpenAIClient()
