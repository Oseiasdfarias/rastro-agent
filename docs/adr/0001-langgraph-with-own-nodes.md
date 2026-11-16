# 0001 LangGraph with our own nodes, calling LiteLLM directly

Status: accepted (2026-11-16)

We need a loop with a step limit, a repeated-call guard, an evidence check and a pause for
human review that survives a restart. LangGraph gives the graph, `interrupt()` and Postgres
checkpoints. The nodes call LiteLLM directly instead of LangChain chat models, so the
messages stay in OpenAI format, the same gateway serves the agent and the fixed pipeline, and
the tests swap the model with a scripted fake.

Cost: no LangChain tool decorators or prebuilt ReAct agent.
