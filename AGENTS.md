# Notes for AI coding agents

Start with `INDEX.yaml`, then read only the folder your task touches.

- All code lives in `src/`: `rastro` (the app), `synthdata` (data + ground truth), `evals`.
- Layer rule: `domain` imports nothing internal; `application` imports only `domain` and
  `application.ports`. `tests/unit/test_layers.py` enforces it.
- Unit tests never need network or models: use the fakes in `tests/fakes.py`.
- Everything runs in Docker: `make help`.
- Data is synthetic. Do not add real company names, real SAP extracts or claims of real use.
- Git: branch `develop`; no commits to `main`.
