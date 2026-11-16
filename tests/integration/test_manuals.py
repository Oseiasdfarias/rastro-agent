import pytest

from rootcause.adapters.db import connect
from rootcause.adapters.manuals.ingest import store_chunks
from rootcause.adapters.manuals.pgvector import PgVectorManuals
from tests.fakes_embed import HashEmbedder

pytestmark = pytest.mark.integration


def test_search_returns_k_with_page(db_url):
    conn = connect(db_url)
    emb = HashEmbedder()
    chunks = [
        (160, "rolamento com ruido e vibracao"),
        (170, "resistencia de aquecimento"),
        (180, "placa de identificacao do motor"),
        (190, "lubrificacao do mancal graxa"),
    ]
    assert store_chunks(conn, chunks, emb) == 4
    hits = PgVectorManuals(conn, emb).search("ruido no rolamento", k=2)
    assert len(hits) == 2
    assert hits[0].page == 160
    assert hits[0].record_id == "MANUAL:160/0"
    assert hits[0].score >= hits[1].score
