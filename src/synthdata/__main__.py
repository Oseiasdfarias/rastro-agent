import argparse

import psycopg

from rootcause.config import get_settings
from synthdata.generator import generate
from synthdata.load import load


def main() -> None:
    p = argparse.ArgumentParser(prog="synthdata")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()
    ds = generate(seed=args.seed)
    with psycopg.connect(get_settings().database_url) as conn:
        load(conn, ds)
    print(f"loaded {sum(len(v) for v in ds.tables.values())} rows, {len(ds.truth)} eval cases")


if __name__ == "__main__":
    main()
