import json
import pytest
from app import assistant as assistant_module
from app.assistant import Assistant
from app.config import Settings
from app.llm import LLMProviderError, LLMResponse, ToolCall
from app.models import Moods, SearchState
from tests.conftest import TODAY

USAGE = {"input_tokens": 100, "cached_input_tokens": 0, "output_tokens": 20}


class FakeLLM:
    model = "gpt-4.1-mini"

    def __init__(self, *responses):
        self.responses = list(responses)
        self.seen = []  

    def create(self, *, system, messages, tools):
        self.seen.append(list(messages))
        nxt = self.responses.pop(0) if self.responses else call("update_search", {})
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


def call(name, args, raw=None):
    tc = ToolCall(id=f"call_{name}", name=name, arguments=args, raw_arguments=raw or json.dumps(args))
    return LLMResponse(text="", tool_calls=[tc], stop="tool_use", usage=USAGE)


def answer(text):
    return LLMResponse(text=text, tool_calls=[], stop="end", usage=USAGE)


def tool_results(llm):
    """Tool messages the model received, parsed."""
    return [m for m in llm.seen[-1] if m["role"] == "tool"]


@pytest.fixture(autouse=True)
def quiet_settings(monkeypatch, tmp_path):
    monkeypatch.setattr(assistant_module, "settings", Settings(turn_log_path=str(tmp_path / "turns.jsonl")))


def make(catalog, *responses):
    llm = FakeLLM(*responses)
    return Assistant(llm=llm, catalog=catalog, today=TODAY), llm


def test_update_search_changes_the_page_search(catalog):
    bot, llm = make(catalog, call("update_search", {"continents": ["Asia"], "max_price": 1000}), answer("Try Thailand!"))

    turn = bot.chat("Asia under 1000 euros", SearchState())

    assert turn.reply == "Try Thailand!"
    assert turn.search.state.continents == ["Asia"]
    assert turn.search.state.max_price == 1000
    assert turn.search.total == 1
    assert turn.meta["tool_calls"] == ["update_search"]
    assert turn.meta["usage"]["input_tokens"] == 200 

    result = json.loads(tool_results(llm)[0]["content"])
    assert result["result_count"] == 1
    assert result["top_results"][0]["title"] == "Thailand Beaches"


def test_clear_removes_only_the_listed_filters(catalog):
    start = SearchState(continents=["Asia"], max_price=1000, moods=Moods(party=60))
    bot, _ = make(catalog, call("update_search", {"clear": ["moods", "max_price"]}), answer("ok"))

    state = bot.chat("forget the budget and the party", start).search.state

    assert state.max_price is None
    assert state.moods.active() == {}
    assert state.continents == ["Asia"]


def test_model_gets_its_mistakes_back_instead_of_crashing(catalog):
    bad_dates = call("update_search", {"date_from": "2027-05-01", "date_to": "2027-04-01"})
    bad_json = call("update_search", None, raw='{"continents": ["Asia"')
    bot, llm = make(catalog, bad_dates, bad_json, answer("Sorry, which dates?"))

    turn = bot.chat("May but back in April", SearchState(continents=["Europe"]))

    errors = tool_results(llm)
    assert all(m["is_error"] for m in errors)
    assert "date_from must be before date_to" in errors[0]["content"]
    assert "not valid JSON" in errors[1]["content"]
    assert turn.search.state.continents == ["Europe"] 


def test_stops_after_max_tool_rounds(catalog, monkeypatch, tmp_path):
    monkeypatch.setattr(assistant_module, "settings", Settings(max_tool_rounds=2, turn_log_path=str(tmp_path / "t.jsonl")))
    bot, llm = make(catalog) 

    turn = bot.chat("anything", SearchState())

    assert len(llm.seen) == 2
    assert "updated the search" in turn.reply


def test_failed_turn_leaves_no_half_conversation(catalog):
    bot, _ = make(catalog, answer("Hi!"), LLMProviderError(429, "busy"))
    first = bot.chat("hello", SearchState())
    history = list(bot.sessions[first.session_id].messages)

    with pytest.raises(LLMProviderError):
        bot.chat("and now?", SearchState(), first.session_id)

    assert bot.sessions[first.session_id].messages == history


def test_every_message_carries_today_and_current_search(catalog):
    bot, llm = make(catalog, answer("ok"))
    bot.chat("cheaper please", SearchState(max_price=1200))

    content = llm.seen[0][0]["content"]
    assert content.startswith("<context>")
    assert "today: 2027-01-10" in content
    assert '"max_price":1200' in content
    assert content.endswith("cheaper please")


def test_faq_search_prefers_the_destination_and_skips_other_countries(catalog):
    bot, _ = make(catalog)
    faqs = bot._tool_search_faqs("visa", destination="Japan")["faqs"]
    assert [f["title"] for f in faqs] == ["Visa for Japan", "Do I need a visa?"]
