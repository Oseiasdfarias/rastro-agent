from dataclasses import dataclass

from rootcause.adapters.crm.postgres import PostgresCrm
from rootcause.adapters.db import connect
from rootcause.adapters.erp.postgres import PostgresErp
from rootcause.adapters.llm.gateway import LlmClient
from rootcause.adapters.manuals.ingest import E5Embedder
from rootcause.adapters.manuals.pgvector import PgVectorManuals
from rootcause.config import Settings
from rootcause.tools.registry import ToolRegistry


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
    llm = LlmClient(models or settings.llm_models, ollama_base_url=settings.ollama_base_url)
    return Deps(conn, crm, erp, manuals, llm, ToolRegistry(erp, crm, manuals), settings.max_steps)
