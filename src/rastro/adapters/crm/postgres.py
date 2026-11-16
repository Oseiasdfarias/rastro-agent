import psycopg

from rastro.adapters import rows
from rastro.domain.models import Case


class PostgresCrm:
    def __init__(self, conn: psycopg.Connection):
        self.conn = conn

    def get_case(self, case_id: str) -> Case | None:
        r = self.conn.execute(
            "SELECT c.*, a.kunnr FROM crm_case c JOIN crm_account a USING (account_id)"
            " WHERE c.case_id = %s",
            (case_id,),
        ).fetchone()
        return rows.case(r) if r else None

    def list_case_ids(self) -> list[str]:
        return [r["case_id"] for r in self.conn.execute("SELECT case_id FROM crm_case ORDER BY 1")]
