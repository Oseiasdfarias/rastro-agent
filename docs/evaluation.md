# Evaluation

`make eval ARGS="--strategy agent|fixed --model <litellm model> [--limit N]"`

## Cases and scoring

The ground truth comes from the generator ([synthetic-data.md](synthetic-data.md)): 30
complaints about batches made inside a planted failure window and 10 about batches far from
any failure. Per case (`src/evals/score.py`):

| Metric | Right when |
|---|---|
| verdict | `factory_cause` / `no_factory_cause` matches the truth |
| equipment, failure mode | match the planted episode (failure cases only) |
| evidence | every cited id exists, and for a failure at least one cited QMEL/AUFK record belongs to the planted equipment inside its window |

## Results (2026-11-16, gemini/gemini-3.1-flash-lite, seed 7)

| Strategy | Verdict | Equipment | Mode | Evidence valid | Noise | Steps | Tokens | s/case |
|---|---|---|---|---|---|---|---|---|
| fixed | 0.975 | 0.967 | 0.967 | 0.975 | 1.0 | 6.9 | 2,127 | 1.8 |
| agent | 0.825 | 0.933 | 0.900 | 0.825 | 1.0 | 6.0 | 12,720 | 7.2 |

Steps for the fixed pipeline are lookups plus the LLM call; for the agent, LLM turns.

Agent misses: wrong verdict in CS-00002, 07, 16, 18, 31, 35, 37; right verdict but wrong
failure mode in CS-00023. In five of the wrong verdicts (02, 07, 18, 31, 37) the report named
the right equipment and failure mode but cited no record; re-running them showed an empty
evidence list every time, and with the current code the report says "no maintenance record cited for
PR-02 / sensor_fault; cause not accepted". CS-00016 and CS-00035 picked the wrong equipment. CS-00002 hit the 8-step limit after checking five candidate batches one
call at a time. Fixed pipeline miss: CS-00038.

The agent was not tuned after seeing these cases; changing prompts or the step limit now and
re-running on the same 40 cases would overstate the result.

## Manual retrieval (2026-11-16)

`rastro eval-manuals`. Queries: the 20 symptom notes of the generator (4 per failure mode).
A returned chunk counts as relevant by a written rule (`src/evals/manuals.py`): for bearing wear
it must mention bearings and a symptom (noise, vibration, temperature, lubrication); for
misalignment it must mention alignment. The indexed manual is for electric motors, so for
heater drift, mold wear and pressure-sensor faults no chunk is relevant and the right answer
is to return nothing.

| Min score | Bearing + misalignment: hit in top 3 | Other modes: nothing returned | Irrelevant chunks returned |
|---|---|---|---|
| none | 4/8 (bearing 4/4, misalignment 0/4) | 0/12 | 55 of 60 |
| 0.85 | 3/8 | 1/12 | 33 of 37 |
| 0.86 | 1/8 | 8/12 | 15 of 16 |
| 0.87 | 1/8 | 10/12 | 2 of 3 |

Scores sit between 0.83 and 0.88 for everything, and queries the manual cannot answer score
as high as the ones it can ("temp. placa abaixo do set" 0.875; the best bearing hit 0.850).
A fixed score threshold cannot separate them, so none is applied. Misalignment fails because
the manual covers coupling alignment on motors, while the notes describe a crooked extruded
profile.

What would fix it: one manual per equipment, with the search filtered by the equipment that
made the batch, and a relevance check that can say "not in this manual". Until then, manual
chunks are context for the model, not evidence: a cause is only accepted with a QMEL/AUFK
record.

## Caveats

- 40 synthetic cases from one seed. One or two cases of difference is noise.
- One small cloud model. A local 3B model on CPU was too slow for long prompts (over 300 s per
  call).
- The fixed pipeline knows the shape of the trail. That is the point of the comparison, and
  also why it is not a general result.
