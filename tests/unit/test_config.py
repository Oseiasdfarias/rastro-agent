from rootcause.config import get_settings


def test_settings_reads_llm_models_list(monkeypatch):
    monkeypatch.setenv("LLM_MODELS", "ollama/qwen2.5:3b,openai/gpt-4o-mini")
    get_settings.cache_clear()
    assert get_settings().llm_models == ["ollama/qwen2.5:3b", "openai/gpt-4o-mini"]


def test_defaults(monkeypatch):
    monkeypatch.delenv("LLM_MODELS", raising=False)
    get_settings.cache_clear()
    s = get_settings()
    assert s.max_steps == 8
    assert s.llm_models == ["ollama/qwen2.5:3b"]
    assert s.embed_model == "intfloat/multilingual-e5-small"
