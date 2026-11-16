# Changelog

## 0.1.0 (2026-11-16)

- Synthetic SAP-format (KNA1, MARA, EQUI, VBAK/VBAP, LIKP/LIPS, AFKO/AFPO, QMEL, AUFK) and CRM
  data with planted failures and ground truth.
- Tools with validated arguments; LangGraph agent with step limit, repeated-call guard,
  evidence check and human review.
- Fixed pipeline baseline and evaluation harness.
- FastAPI service with Postgres checkpoints, Redis cache, Langfuse tracing, Docker Compose.
