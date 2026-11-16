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
evidence list every time, and with the current code the report says "no record cited for
PR-02 / sensor_fault; cause not accepted". CS-00016 and CS-00035 picked the wrong equipment. CS-00002 hit the 8-step limit after checking five candidate batches one
call at a time. Fixed pipeline miss: CS-00038.

The agent was not tuned after seeing these cases; changing prompts or the step limit now and
re-running on the same 40 cases would overstate the result.

## Caveats

- 40 synthetic cases from one seed. One or two cases of difference is noise.
- One small cloud model. A local 3B model on CPU was too slow for long prompts (over 300 s per
  call).
- The fixed pipeline knows the shape of the trail. That is the point of the comparison, and
  also why it is not a general result.
