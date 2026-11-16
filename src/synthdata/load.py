from importlib.resources import files

import psycopg
from psycopg import sql

from synthdata.generator import Dataset

TABLES = [
    "KNA1",
    "MARA",
    "EQUI",
    "AFKO",
    "AFPO",
    "VBAK",
    "VBAP",
    "LIKP",
    "LIPS",
    "QMEL",
    "AUFK",
    "crm_account",
    "crm_case",
]


def load(conn: psycopg.Connection, ds: Dataset) -> None:
    with conn.transaction(), conn.cursor() as cur:
        cur.execute(files("synthdata").joinpath("schema.sql").read_text())
        names = [t.lower() for t in TABLES] + ["eval_truth"]
        cur.execute(sql.SQL("TRUNCATE {}").format(sql.SQL(", ").join(map(sql.Identifier, names))))
        for table in TABLES:
            rows = ds.tables[table]
            cols = list(rows[0])
            stmt = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table.lower()),
                sql.SQL(", ").join(map(sql.Identifier, cols)),
                sql.SQL(", ").join(sql.Placeholder() * len(cols)),
            )
            cur.executemany(stmt, [tuple(r[c] for c in cols) for r in rows])
        cur.executemany(
            "INSERT INTO eval_truth VALUES (%s, %s, %s, %s, %s, %s, %s)",
            [
                (
                    g.case_id,
                    g.verdict.value,
                    g.equnr,
                    g.failure_mode and g.failure_mode.value,
                    g.window_start,
                    g.window_end,
                    ds.hidden_vbeln[g.case_id],
                )
                for g in ds.truth
            ],
        )
