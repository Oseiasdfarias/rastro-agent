from types import SimpleNamespace as NS

import pytest

from rastro.adapters.llm.gateway import LlmClient
from rastro.application.ports import LlmUnavailable


def _resp(content=None, tool_calls=None):
    msg = NS(content=content, tool_calls=tool_calls)
    return NS(choices=[NS(message=msg)], usage=NS(total_tokens=42))


def test_gateway_falls_back_to_second_model():
    calls = []

    def completion(model, **kw):
        calls.append(model)
        if model.startswith("ollama"):
            raise ConnectionError("down")
        return _resp("ok")

    llm = LlmClient(["ollama/qwen2.5:3b", "openai/gpt-4o-mini"], completion=completion)
    r = llm.chat([{"role": "user", "content": "hi"}])
    assert r.content == "ok" and r.model == "openai/gpt-4o-mini" and r.tokens == 42
    assert calls == ["ollama_chat/qwen2.5:3b", "openai/gpt-4o-mini"]


def test_gateway_raises_unavailable_when_all_fail():
    def completion(model, **kw):
        raise ConnectionError("down")

    with pytest.raises(LlmUnavailable):
        LlmClient(["ollama/qwen2.5:3b"], completion=completion).chat([])


def test_tool_calls_parsed():
    tc = NS(id="t1", function=NS(name="get_case", arguments='{"case_id": "CS-1"}'))
    llm = LlmClient(["x/y"], completion=lambda model, **kw: _resp(None, [tc]))
    [call] = llm.chat([]).tool_calls
    assert (call.id, call.name, call.arguments) == ("t1", "get_case", '{"case_id": "CS-1"}')


def test_inline_json_tool_call_in_content_is_recovered():
    content = '{"name": "get_case", "arguments": {"case_id": "CS-1"}}'
    llm = LlmClient(["x/y"], completion=lambda model, **kw: _resp(content))
    r = llm.chat([], tools=[{"type": "function", "function": {"name": "get_case"}}])
    assert r.tool_calls[0].name == "get_case" and r.content is None


def test_ollama_gets_large_context_window():
    seen = {}

    def completion(model, **kw):
        seen.update(kw)
        return _resp("ok")

    LlmClient(
        ["ollama/qwen2.5:3b"],
        ollama_base_url="http://o:11434",
        completion=completion,
        num_ctx=16384,
    ).chat([])
    assert seen["num_ctx"] == 16384 and seen["api_base"] == "http://o:11434"
