from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from random import Random

from pydantic import BaseModel, ConfigDict

from rootcause.domain.models import FailureMode, Verdict
from synthdata import texts

START = date(2026, 1, 5)
DAYS = 182
N_EPISODES = 8
CITIES = ["Campinas", "Joinville", "Caxias do Sul", "Betim", "Sorocaba", "Contagem", "Curitiba"]


class GroundTruth(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    verdict: Verdict
    equnr: str | None = None
    failure_mode: FailureMode | None = None
    window_start: date | None = None
    window_end: date | None = None


@dataclass
class Dataset:
    tables: dict[str, list[dict]]
    truth: list[GroundTruth]
    hidden_vbeln: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Episode:
    equnr: str
    mode: FailureMode
    start: date
    end: date

    def covers(self, equnr: str, day: date, margin: int = 0) -> bool:
        m = timedelta(days=margin)
        return equnr == self.equnr and self.start - m <= day <= self.end + m


@dataclass(frozen=True)
class _Batch:
    charg: str
    equnr: str
    day: date
    matnr: str
    vbeln: str
    kunnr: str
    delivered_on: date


def generate(seed: int = 7, n_fault_cases: int = 30, n_noise_cases: int = 10) -> Dataset:
    rng = Random(seed)
    t: dict[str, list[dict]] = {
        k: []
        for k in [
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
    }
    maktx = dict(texts.MATERIALS)

    for i in range(40):
        kunnr = f"{100001 + i:010d}"
        name = f"Cliente Industrial {i + 1:02d} Ltda"
        t["KNA1"].append({"kunnr": kunnr, "name1": name, "ort01": rng.choice(CITIES)})
        t["crm_account"].append({"account_id": f"ACC-{i + 1:04d}", "kunnr": kunnr, "name": name})
    account_of = {a["kunnr"]: a["account_id"] for a in t["crm_account"]}
    t["MARA"] = [{"matnr": m, "maktx": d, "mtart": "FERT"} for m, d in texts.MATERIALS]
    t["EQUI"] = [{"equnr": e, "eqktx": d, "arbpl": f"WC-{e}"} for e, d, _ in texts.EQUIPMENT]

    episodes = []
    for k in range(N_EPISODES):
        equnr = texts.EQUIPMENT[k % 6][0]
        start = START + timedelta(days=rng.randint(14, 50) if k < 6 else rng.randint(75, 110))
        mode = rng.choice(texts.MODES_BY_KIND[equnr[:2]])
        episodes.append(_Episode(equnr, mode, start, start + timedelta(days=rng.randint(7, 21))))

    batches = _production(rng, t)
    _maintenance(rng, t, episodes)

    chosen: list[tuple[_Batch, _Episode | None]] = []
    counts = [n_fault_cases // N_EPISODES] * N_EPISODES
    for k in rng.sample(range(N_EPISODES), n_fault_cases % N_EPISODES):
        counts[k] += 1
    for ep, n in zip(episodes, counts, strict=True):
        pool = [b for b in batches if ep.covers(b.equnr, b.day)]
        chosen += [(b, ep) for b in rng.sample(pool, n)]
    healthy = [b for b in batches if not any(e.covers(b.equnr, b.day, 3) for e in episodes)]
    healthy = [b for b in healthy if b.day <= START + timedelta(days=DAYS - 60)]
    chosen += [(b, None) for b in rng.sample(healthy, n_noise_cases)]
    rng.shuffle(chosen)

    truth, hidden = [], {}
    for n, (b, ep) in enumerate(chosen, start=1):
        case_id = f"CS-{n:05d}"
        created = b.delivered_on + timedelta(days=rng.randint(14, 42))
        if ep:
            text = rng.choice(texts.COMPLAINT_TEXTS[ep.mode])
            truth.append(
                GroundTruth(
                    case_id=case_id,
                    verdict=Verdict.factory_cause,
                    equnr=ep.equnr,
                    failure_mode=ep.mode,
                    window_start=ep.start,
                    window_end=ep.end,
                )
            )
        else:
            text = rng.choice(texts.NOISE_TEXTS)
            truth.append(GroundTruth(case_id=case_id, verdict=Verdict.no_factory_cause))
        hidden[case_id] = b.vbeln
        t["crm_case"].append(
            {
                "case_id": case_id,
                "account_id": account_of[b.kunnr],
                "created_on": created,
                "matnr": b.matnr,
                "vbeln": b.vbeln,
                "text": f"{maktx[b.matnr]}, entrega {b.vbeln}. {text}",
            }
        )

    _damage_delivery_numbers(rng, t, batches, episodes, truth)
    return Dataset(tables=t, truth=truth, hidden_vbeln=hidden)


def _production(rng: Random, t: dict[str, list[dict]]) -> list[_Batch]:
    batches, prod_no, so_no, dl_no = [], 1000000001, 10000001, 80000001
    kunnrs = [c["kunnr"] for c in t["KNA1"]]
    for d in range(DAYS):
        day = START + timedelta(days=d)
        for equnr, _, mats in texts.EQUIPMENT:
            for shift in (0, 1):
                start = datetime.combine(day, time(6 + 12 * shift))
                matnr, aufnr = rng.choice(mats), str(prod_no)
                charg = f"B{day:%y%m%d}{equnr.replace('-', '')}{shift + 1}"
                qty = rng.randint(400, 1200)
                t["AFKO"].append(
                    {
                        "aufnr": aufnr,
                        "matnr": matnr,
                        "arbpl": f"WC-{equnr}",
                        "gstrp": start,
                        "gltrp": start + timedelta(hours=12),
                    }
                )
                t["AFPO"].append(
                    {"aufnr": aufnr, "posnr": "0001", "charg": charg, "matnr": matnr, "psmng": qty}
                )
                kunnr, vbeln, so = rng.choice(kunnrs), str(dl_no), str(so_no)
                delivered = day + timedelta(days=rng.randint(2, 10))
                t["VBAK"].append({"vbeln": so, "kunnr": kunnr, "erdat": day})
                t["VBAP"].append({"vbeln": so, "posnr": "000010", "matnr": matnr, "kwmeng": qty})
                t["LIKP"].append(
                    {"vbeln": vbeln, "kunnr": kunnr, "wadat_ist": delivered, "vgbel": so}
                )
                t["LIPS"].append(
                    {
                        "vbeln": vbeln,
                        "posnr": "000010",
                        "matnr": matnr,
                        "charg": charg,
                        "lfimg": qty,
                    }
                )
                batches.append(_Batch(charg, equnr, day, matnr, vbeln, kunnr, delivered))
                prod_no, so_no, dl_no = prod_no + 1, so_no + 1, dl_no + 1
    return batches


def _maintenance(rng: Random, t: dict[str, list[dict]], episodes: list[_Episode]) -> None:
    qm, pm = [300000001], [4000000001]

    def note(equnr: str, day: date, text: str) -> None:
        t["QMEL"].append(
            {"qmnum": f"{qm[0]:09d}", "qmart": "M1", "equnr": equnr, "qmdat": day, "qmtxt": text}
        )
        qm[0] += 1

    def order(equnr: str, day: date, auart: str, text: str) -> None:
        t["AUFK"].append(
            {"aufnr": str(pm[0]), "auart": auart, "equnr": equnr, "erdat": day, "ktext": text}
        )
        pm[0] += 1

    for equnr, _, _ in texts.EQUIPMENT:
        for d in range(rng.randint(0, 13), DAYS, 14):
            order(equnr, START + timedelta(days=d), "PM02", texts.ROUTINE_ORDER)
        d = rng.randint(0, 6)
        while d < DAYS:
            note(equnr, START + timedelta(days=d), rng.choice(texts.ROUTINE_NOTES))
            d += rng.randint(5, 9)
    for ep in episodes:
        span = (ep.end - ep.start).days
        n = rng.randint(2, 4)
        days = sorted(rng.sample(range(span), n))
        for i, d in enumerate(days):
            note(ep.equnr, ep.start + timedelta(days=d), texts.SYMPTOM_NOTES[ep.mode][i])
        order(ep.equnr, ep.end, "PM01", texts.REPAIRS[ep.mode])


def _damage_delivery_numbers(
    rng: Random,
    t: dict[str, list[dict]],
    batches: list[_Batch],
    episodes: list[_Episode],
    truth: list[GroundTruth],
) -> None:
    # Only where customer + material in the last 90 days still points to a single suspect batch.
    kunnr_of = {a["account_id"]: a["kunnr"] for a in t["crm_account"]}
    known = {r["vbeln"] for r in t["LIPS"]}
    eligible = []
    for case, gt in zip(t["crm_case"], truth, strict=True):
        if gt.verdict is not Verdict.factory_cause:
            continue
        kunnr, created = kunnr_of[case["account_id"]], case["created_on"]
        suspects = [
            b
            for b in batches
            if b.kunnr == kunnr
            and b.matnr == case["matnr"]
            and created - timedelta(days=90) <= b.delivered_on <= created
            and any(e.covers(b.equnr, b.day) for e in episodes)
        ]
        if len(suspects) == 1:
            eligible.append(case)
    for i, case in enumerate(rng.sample(eligible, min(9, len(eligible)))):
        if i < 6:
            case["text"] = case["text"].replace(f", entrega {case['vbeln']}", "")
            case["vbeln"] = None
        else:
            wrong = case["vbeln"][:-2] + case["vbeln"][-1] + case["vbeln"][-2]
            if wrong in known or wrong == case["vbeln"]:
                wrong = "9" + case["vbeln"][1:]
            case["text"] = case["text"].replace(case["vbeln"], wrong)
            case["vbeln"] = wrong
