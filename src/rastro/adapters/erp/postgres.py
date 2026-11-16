from datetime import date

import psycopg
from psycopg import sql

from rastro.adapters import rows
from rastro.domain.models import BatchOrigin, Delivery, MaintenanceEvent
from rastro.domain.records import parse_id

_DELIVERY = """SELECT p.vbeln, p.posnr, p.matnr, p.charg, k.kunnr, k.wadat_ist
               FROM lips p JOIN likp k USING (vbeln)"""


class PostgresErp:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_delivery(self, vbeln: str) -> list[Delivery]:
        cur = self.conn.execute(_DELIVERY + " WHERE p.vbeln = %s ORDER BY p.posnr", (vbeln,))
        return [rows.delivery(r) for r in cur]

    def find_deliveries(
        self, kunnr: str, matnr: str | None, since: date, until: date
    ) -> list[Delivery]:
        cur = self.conn.execute(
            _DELIVERY + " WHERE k.kunnr = %s AND (%s::text IS NULL OR p.matnr = %s)"
            " AND k.wadat_ist BETWEEN %s AND %s ORDER BY k.wadat_ist, p.vbeln",
            (kunnr, matnr, matnr, since, until),
        )
        return [rows.delivery(r) for r in cur]

    def get_batch_origin(self, charg: str) -> BatchOrigin | None:
        r = self.conn.execute(
            """SELECT p.charg, a.aufnr, a.arbpl, e.equnr, a.gstrp, a.gltrp
               FROM afpo p JOIN afko a USING (aufnr) JOIN equi e ON e.arbpl = a.arbpl
               WHERE p.charg = %s""",
            (charg,),
        ).fetchone()
        return rows.origin(r) if r else None

    def get_equipment_history(self, equnr: str, start: date, end: date) -> list[MaintenanceEvent]:
        args = (equnr, start, end)
        notes = self.conn.execute(
            "SELECT * FROM qmel WHERE equnr = %s AND qmdat BETWEEN %s AND %s", args
        )
        events = [rows.note(r) for r in notes]
        orders = self.conn.execute(
            "SELECT * FROM aufk WHERE equnr = %s AND erdat BETWEEN %s AND %s", args
        )
        events += [rows.order(r) for r in orders]
        return sorted(events, key=lambda e: (e.on, e.record_id))

    def record_exists(self, record_id: str) -> bool:
        try:
            table, keys = parse_id(record_id)
        except ValueError:
            return False
        if table not in rows.KEYS:
            return False
        name, cols = rows.KEYS[table]
        if len(keys) != len(cols):
            return False
        where = sql.SQL(" AND ").join(sql.SQL("{} = %s").format(sql.Identifier(c)) for c in cols)
        stmt = sql.SQL("SELECT 1 FROM {} WHERE {}").format(sql.Identifier(name), where)
        return self.conn.execute(stmt, keys).fetchone() is not None
