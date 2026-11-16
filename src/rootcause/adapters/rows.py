from rootcause.domain.models import BatchOrigin, Case, Delivery, MaintenanceEvent
from rootcause.domain.records import make_id


def delivery(r: dict) -> Delivery:
    return Delivery(
        vbeln=r["vbeln"],
        posnr=r["posnr"],
        matnr=r["matnr"],
        charg=r["charg"],
        kunnr=r["kunnr"],
        delivered_on=r["wadat_ist"],
    )


def origin(r: dict) -> BatchOrigin:
    return BatchOrigin(
        charg=r["charg"],
        aufnr=r["aufnr"],
        arbpl=r["arbpl"],
        equnr=r["equnr"],
        start=r["gstrp"],
        end=r["gltrp"],
    )


def note(r: dict) -> MaintenanceEvent:
    return MaintenanceEvent(
        record_id=make_id("QMEL", r["qmnum"]),
        equnr=r["equnr"],
        on=r["qmdat"],
        kind="note",
        text=r["qmtxt"],
    )


def order(r: dict) -> MaintenanceEvent:
    return MaintenanceEvent(
        record_id=make_id("AUFK", r["aufnr"]),
        equnr=r["equnr"],
        on=r["erdat"],
        kind="order",
        text=f"[{r['auart']}] {r['ktext']}",
    )


def case(r: dict) -> Case:
    return Case(
        case_id=r["case_id"],
        account_id=r["account_id"],
        kunnr=r["kunnr"],
        created_on=r["created_on"],
        matnr=r["matnr"],
        vbeln=r["vbeln"],
        text=r["text"],
    )


# table -> (sql table, key columns); MANUAL ids live in the manuals store, not the ERP.
KEYS = {
    "Case": ("crm_case", ("case_id",)),
    "KNA1": ("kna1", ("kunnr",)),
    "MARA": ("mara", ("matnr",)),
    "LIKP": ("likp", ("vbeln",)),
    "LIPS": ("lips", ("vbeln", "posnr")),
    "AFKO": ("afko", ("aufnr",)),
    "AFPO": ("afpo", ("aufnr", "posnr")),
    "EQUI": ("equi", ("equnr",)),
    "QMEL": ("qmel", ("qmnum",)),
    "AUFK": ("aufk", ("aufnr",)),
}
