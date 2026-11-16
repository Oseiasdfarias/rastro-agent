# 0002 pgvector instead of Chroma for the manuals

Status: accepted (2026-11-16)

The ERP tables and the checkpoints already live in Postgres. Keeping the manual vectors there
removes one service. The retrieval settings come from the measurements in rag-manual-poc
(multilingual-e5-small, 800-character chunks with 150 overlap, Portuguese section of the WEG
manual), which used Chroma; the numbers there are not re-measured here.
