# Contributing

- Work on a branch from `develop`; open the pull request against `develop`. Nothing goes straight to `main`.
- Run `make lint test` before pushing. Integration tests: `make up && make test-int`.
- New tool for the agent: add the argument model in `src/rastro/tools/specs.py`, the handler in
  `registry.py`, and a test in `tests/unit/tools/`.
- New data source: implement the port in `src/rastro/application/ports.py` under
  `src/rastro/adapters/`, and wire it in `composition.py`. `domain/` and `application/` must
  not import adapters (checked by `tests/unit/test_layers.py`).
- Changing prompts or the data generator changes the evaluation. Re-run `make eval` and update
  `results/` in the same pull request.
