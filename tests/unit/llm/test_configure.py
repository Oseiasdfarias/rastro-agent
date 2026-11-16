import litellm

from rastro.adapters.llm.gateway import LlmClient, configure_litellm


def test_configure_enables_langfuse_and_redis_cache(monkeypatch):
    monkeypatch.setattr(litellm, "callbacks", [])
    monkeypatch.setattr(litellm, "cache", None)
    assert configure_litellm("redis://redis:6379/0", langfuse=True) is True
    assert "langfuse_otel" in litellm.callbacks
    assert litellm.cache is not None


def test_configure_without_redis_or_langfuse(monkeypatch):
    monkeypatch.setattr(litellm, "callbacks", [])
    monkeypatch.setattr(litellm, "cache", None)
    assert configure_litellm(None, langfuse=False) is False
    assert litellm.callbacks == [] and litellm.cache is None


def test_client_asks_for_cache_when_enabled():
    seen = {}

    def completion(model, **kw):
        seen.update(kw)
        raise ConnectionError

    try:
        LlmClient(["x/y"], completion=completion, cache=True).chat([])
    except Exception:
        pass
    assert seen["caching"] is True
