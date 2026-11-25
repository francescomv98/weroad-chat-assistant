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


class LLMProviderError(Exception):
    """Provider failure, mapped to an HTTP status the API can return."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


class LLMClient(Protocol):
    model: str

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse: ...


# USD per million tokens: (input, cached input, output). 
PRICES = {
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
    def __init__(self, model: str | None = None, reasoning_effort: str | None = None) -> None:
        self.model = model or settings.openai_model
        self.effort = reasoning_effort if reasoning_effort is not None else settings.openai_reasoning_effort
        self.prompt_cache_key = settings.openai_prompt_cache_key
        self._client = None

    def _get_client(self):
        import openai

        if self._client is None:
            try:
                self._client = openai.OpenAI(timeout=60.0)  
            except openai.OpenAIError as e:
                raise LLMProviderError(500, "No OpenAI credentials: set OPENAI_API_KEY in .env") from e
        return self._client

    def create(self, *, system: str, messages: list[dict], tools: list[dict]) -> LLMResponse:
        import openai

        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=to_openai_messages(system, messages),
            tools=to_openai_tools(tools),
            max_completion_tokens=8000,
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
                "output_tokens": completion.usage.completion_tokens,
            }
        return LLMResponse(text=msg.content or "", tool_calls=tool_calls, stop=stop, usage=usage)


def make_client() -> LLMClient:
    return OpenAIClient()
