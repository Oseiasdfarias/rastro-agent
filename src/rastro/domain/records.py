TABLES = frozenset(
    {"Case", "KNA1", "MARA", "LIKP", "LIPS", "AFKO", "AFPO", "EQUI", "QMEL", "AUFK", "MANUAL"}
)


def make_id(table: str, *keys: str) -> str:
    if table not in TABLES:
        raise ValueError(f"unknown table: {table}")
    return f"{table}:{'/'.join(keys)}"


def parse_id(record_id: str) -> tuple[str, tuple[str, ...]]:
    table, sep, rest = record_id.partition(":")
    if not sep or table not in TABLES or not rest:
        raise ValueError(f"invalid record id: {record_id}")
    return table, tuple(rest.split("/"))
