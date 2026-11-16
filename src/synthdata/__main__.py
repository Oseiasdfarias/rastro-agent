import argparse
from pathlib import Path

import psycopg

from rootcause.adapters.db import connect
from rootcause.adapters.manuals.ingest import E5Embedder, download, ingest
from rootcause.config import get_settings
from synthdata.generator import generate
from synthdata.load import load


def main() -> None:
    p = argparse.ArgumentParser(prog="synthdata")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--skip-manuals", action="store_true")
    p.add_argument("--manual", type=Path, default=Path("data/manual.pdf"))
    args = p.parse_args()
    ds = generate(seed=args.seed)
    with psycopg.connect(get_settings().database_url) as conn:
        load(conn, ds)
    print(f"loaded {sum(len(v) for v in ds.tables.values())} rows, {len(ds.truth)} eval cases")
    if not args.skip_manuals:
        s = get_settings()
        n = ingest(connect(s.database_url), download(args.manual), E5Embedder(s.embed_model))
        print(f"indexed {n} manual chunks")


if __name__ == "__main__":
    main()
