from dataclasses import dataclass

from rastro.adapters.crm.postgres import PostgresCrm
from rastro.adapters.db import connect
from rastro.adapters.erp.postgres import PostgresErp
from rastro.adapters.llm.gateway import LlmClient, configure_litellm
from rastro.adapters.manuals.ingest import E5Embedder
from rastro.adapters.manuals.pgvector import PgVectorManuals
from rastro.config import Settings
from rastro.tools.registry import ToolRegistry


@dataclass
class Deps:
    conn: object
    crm: PostgresCrm
    erp: PostgresErp
    manuals: PgVectorManuals
    llm: LlmClient
    tools: ToolRegistry
    max_steps: int


def build(settings: Settings, models: list[str] | None = None) -> Deps:
    conn = connect(settings.database_url)
    crm, erp = PostgresCrm(conn), PostgresErp(conn)
    manuals = PgVectorManuals(conn, E5Embedder(settings.embed_model))
    cache = settings.llm_cache and configure_litellm(settings.redis_url, settings.langfuse_enabled)
    if not settings.llm_cache:
        configure_litellm(None, settings.langfuse_enabled)
    llm = LlmClient(
        models or settings.llm_models, ollama_base_url=settings.ollama_base_url, cache=cache
    )
    return Deps(conn, crm, erp, manuals, llm, ToolRegistry(erp, crm, manuals), settings.max_steps)
