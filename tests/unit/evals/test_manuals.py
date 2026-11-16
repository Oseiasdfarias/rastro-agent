from evals.manuals import is_relevant, score_queries
from rastro.domain.models import FailureMode, ManualPassage


def p(text, score=0.9, page=200):
    return ManualPassage(record_id=f"MANUAL:{page}/0", page=page, text=text, score=score)


def test_bearing_needs_component_and_symptom():
    assert is_relevant(FailureMode.bearing_wear, "Ruído nos rolamentos indica desgaste")
    assert not is_relevant(FailureMode.bearing_wear, "Tipos de rolamentos e dimensões")
    assert not is_relevant(FailureMode.bearing_wear, "Vibração do motor na base")


def test_uncovered_modes_never_relevant():
    assert not is_relevant(FailureMode.heater_drift, "Resistência de aquecimento do motor")
    assert is_relevant(FailureMode.misalignment, "Verifique o alinhamento do acoplamento")


class FakeManuals:
    def __init__(self, hits):
        self.hits = hits

    def search(self, query, k=4):
        return self.hits[:k]


def test_score_queries_hit_and_refusal():
    good = FakeManuals(
        [p("Ruído no rolamento: lubrificar", 0.85), p("Placa de identificação", 0.8)]
    )
    m = score_queries(
        good,
        {FailureMode.bearing_wear: ["ruido mancal"], FailureMode.heater_drift: ["temp placa"]},
        k=3,
        min_score=0.82,
    )
    assert m["covered_hit_at_k"] == 1.0
    assert m["uncovered_refusal"] == 0.0
    assert m["irrelevant_returned"] == 1
    none = score_queries(good, {FailureMode.heater_drift: ["temp placa"]}, k=3, min_score=0.9)
    assert none["uncovered_refusal"] == 1.0 and none["irrelevant_returned"] == 0
