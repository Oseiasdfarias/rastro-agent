import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from rootcause.domain.models import ManualPassage


class PgVectorManuals:
    def __init__(self, conn: psycopg.Connection, embedder):
        register_vector(conn)
        self.conn, self.embedder = conn, embedder

    def search(self, query: str, k: int = 4) -> list[ManualPassage]:
        [q] = self.embedder.encode([query], "query")
        cur = self.conn.execute(
            "SELECT record_id, page, text, 1 - (embedding <=> %s) AS score"
            " FROM manual_chunks ORDER BY embedding <=> %s LIMIT %s",
            (np.array(q, dtype=np.float32),) * 2 + (k,),
        )
        return [ManualPassage(**r) for r in cur]
