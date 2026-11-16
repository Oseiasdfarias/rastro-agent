# 0003 Eval and investigate run on the host network

Status: accepted (2026-11-16)

A default Ollama install listens on 127.0.0.1, which containers cannot reach through
`host.docker.internal`. The `cli` service uses `network_mode: host` so `make eval` works
without changing the host's Ollama. The `api` service stays on the compose network; it needs
`OLLAMA_HOST=0.0.0.0` on the host, a cloud model in `LLM_MODELS`, or the `local-llm` profile.

Cost: `network_mode: host` is Linux only.
