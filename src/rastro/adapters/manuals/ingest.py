import logging
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Literal, Protocol

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from pypdf import PdfReader

from rastro.domain.records import make_id

MANUAL_URL = (
    "https://static.weg.net/medias/downloadcenter/ha6/h39/"
    "WEG-WMO-safe-area-50033244-manual-pt-en-es.pdf"
)
PT_PAGES = (157, 233)  # Portuguese section, same range used in rag-manual-poc
DIM = 384


class Embedder(Protocol):
    def encode(self, texts: list[str], kind: Literal["query", "passage"]) -> list[list[float]]: ...


class E5Embedder:
    def __init__(self, model: str):
        from sentence_transformers import SentenceTransformer

        self._m = SentenceTransformer(model, device="cpu")

    def encode(self, texts, kind):
        vecs = self._m.encode([f"{kind}: {t}" for t in texts], normalize_embeddings=True)
        return [v.tolist() for v in vecs]


def chunk_pages(
    pages: list[str], size: int = 800, overlap: int = 150, first_page: int = 1
) -> list[tuple[int, str]]:
    out = []
    for i, text in enumerate(pages):
        text = re.sub(r"\s+", " ", text).strip()
        for start in range(0, max(len(text) - overlap, 1), size - overlap):
            if piece := text[start : start + size]:
                out.append((first_page + i, piece))
    return out


def ensure_schema(conn: psycopg.Connection) -> None:
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS manual_chunks (
              record_id text PRIMARY KEY, page int, text text, embedding vector({DIM}))"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS manual_chunks_hnsw ON manual_chunks"
        " USING hnsw (embedding vector_cosine_ops)"
    )


def store_chunks(conn: psycopg.Connection, chunks: list[tuple[int, str]], embedder) -> int:
    ensure_schema(conn)
    seen: Counter[int] = Counter()
    rows = []
    for page, text in chunks:
        rows.append((make_id("MANUAL", str(page), str(seen[page])), page, text))
        seen[page] += 1
    vecs = []
    for i in range(0, len(rows), 64):
        vecs += embedder.encode([r[2] for r in rows[i : i + 64]], "passage")
    with conn.transaction():
        conn.execute("TRUNCATE manual_chunks")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO manual_chunks VALUES (%s, %s, %s, %s)",
                [(*r, np.array(v, dtype=np.float32)) for r, v in zip(rows, vecs, strict=True)],
            )
    return len(rows)


def download(path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MANUAL_URL, path)
    return path


def ingest(conn: psycopg.Connection, pdf_path: Path, embedder) -> int:
    logging.getLogger("pypdf").setLevel(logging.ERROR)
    reader = PdfReader(pdf_path)
    first, last = PT_PAGES
    pages = [reader.pages[i].extract_text() or "" for i in range(first - 1, last)]
    return store_chunks(conn, chunk_pages(pages, first_page=first), embedder)
