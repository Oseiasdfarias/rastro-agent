import json
import logging
import uuid
from collections.abc import Callable

from pydantic import BaseModel

from rootcause.application.ports import ChatResult, LlmUnavailable, ToolCall

log = logging.getLogger(__name__)


def _litellm_completion(model: str, **kw):
    import litellm

    return litellm.completion(model=model, **kw)


def _route(model: str) -> str:
    # ollama_chat speaks the chat API, which is what tool calling needs
    return "ollama_chat/" + model.removeprefix("ollama/") if model.startswith("ollama/") else model


class LlmClient:
    def __init__(
        self,
        models: list[str],
        ollama_base_url: str | None = None,
        completion: Callable | None = None,
        timeout: float = 300,
    ):
        self.models, self.ollama_base_url = models, ollama_base_url
        self._completion = completion or _litellm_completion
        self.timeout = timeout

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        response_format: type[BaseModel] | None = None,
    ) -> ChatResult:
        errors = []
        for model in self.models:
            kw: dict = {"messages": messages, "temperature": 0, "timeout": self.timeout}
            if tools:
                kw["tools"] = tools
            if response_format:
                kw["response_format"] = response_format
            if model.startswith("ollama/") and self.ollama_base_url:
                kw["api_base"] = self.ollama_base_url
            try:
                resp = self._completion(_route(model), **kw)
            except Exception as e:  # noqa: BLE001 - any provider failure moves to the next one
                log.warning("model %s failed: %s", model, e)
                errors.append(f"{model}: {e}")
                continue
            return _parse(resp, model, tools)
        raise LlmUnavailable("; ".join(errors) or "no model configured")


def _parse(resp, model: str, tools: list[dict] | None) -> ChatResult:
    msg = resp.choices[0].message
    calls = [
        ToolCall(
            id=tc.id or uuid.uuid4().hex[:8],
            name=tc.function.name,
            arguments=tc.function.arguments or "{}",
        )
        for tc in (msg.tool_calls or [])
    ]
    content = msg.content
    if not calls and tools and content and (inline := _inline_call(content, tools)):
        calls, content = [inline], None
    usage = getattr(resp, "usage", None)
    return ChatResult(
        content=content,
        tool_calls=calls,
        tokens=getattr(usage, "total_tokens", 0) or 0,
        model=model,
    )


def _inline_call(content: str, tools: list[dict]) -> ToolCall | None:
    # small models sometimes write the tool call as JSON text instead of a real call
    text = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        obj = json.loads(text)
    except ValueError:
        return None
    names = {t["function"]["name"] for t in tools}
    if isinstance(obj, dict) and obj.get("name") in names:
        args = obj.get("arguments", obj.get("parameters", {}))
        return ToolCall(
            id=uuid.uuid4().hex[:8],
            name=obj["name"],
            arguments=args if isinstance(args, str) else json.dumps(args),
        )
    return None
