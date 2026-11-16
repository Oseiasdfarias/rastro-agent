import os

import psycopg
import pytest


@pytest.fixture(scope="session")
def db_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set")
    return url


@pytest.fixture(scope="session")
def loaded_db(db_url):
    from synthdata.generator import generate
    from synthdata.load import load

    ds = generate(seed=7)
    with psycopg.connect(db_url) as conn:
        load(conn, ds)
    return ds


@pytest.fixture
def conn(db_url):
    with psycopg.connect(db_url) as c:
        yield c
