import re

from rastro.application.ports import ManualsPort
from rastro.domain.models import FailureMode

# The indexed manual is for electric motors. It covers bearings and alignment; it has nothing
# on press heater plates, molds or pressure transducers, so for those the right answer is none.
_RULES = {
    FailureMode.bearing_wear: (
        r"rolament|mancal|mancais",
        r"ru[ií]do|vibra|temperat|lubrifica|graxa",
    ),
    FailureMode.misalignment: (r"alinhament", r""),
}
COVERED = frozenset(_RULES)


def is_relevant(mode: FailureMode, text: str) -> bool:
    if mode not in _RULES:
        return False
    component, symptom = _RULES[mode]
    t = text.lower()
    return bool(re.search(component, t)) and (not symptom or bool(re.search(symptom, t)))


def score_queries(
    manuals: ManualsPort, queries: dict[FailureMode, list[str]], k: int = 3, min_score: float = 0.0
) -> dict:
    hits = covered = refused = uncovered = irrelevant = returned = 0
    for mode, qs in queries.items():
        for q in qs:
            top = [h for h in manuals.search(q, k=k) if h.score >= min_score]
            rel = [h for h in top if is_relevant(mode, h.text)]
            returned += len(top)
            irrelevant += len(top) - len(rel)
            if mode in COVERED:
                covered += 1
                hits += bool(rel)
            else:
                uncovered += 1
                refused += not top
    return {
        "min_score": min_score,
        "covered_hit_at_k": round(hits / covered, 3) if covered else None,
        "uncovered_refusal": round(refused / uncovered, 3) if uncovered else None,
        "irrelevant_returned": irrelevant,
        "returned": returned,
    }
