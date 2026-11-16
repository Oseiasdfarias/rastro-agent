# rootcause-agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agente que vai de uma reclamação no CRM até a causa provável na fábrica (dados sintéticos no formato SAP), medido contra um pipeline fixo, tudo rodando em Docker.

**Architecture:** Pacote `rootcause` em camadas (domain → application/ports → adapters, ligados em `composition.py`). O agente é um `StateGraph` do LangGraph com nós próprios (llm, tools, finalize, review) que chamam o LiteLLM direto; a revisão humana usa `interrupt()` com checkpoint no Postgres. `synthdata` gera os dados e o gabarito; `evals` mede agente e pipeline fixo.

**Tech Stack:** Python 3.12, uv, Pydantic v2, psycopg 3, pgvector, sentence-transformers (intfloat/multilingual-e5-small, CPU), pypdf, LangGraph + langgraph-checkpoint-postgres, LiteLLM (Router, cache Redis, callback Langfuse), FastAPI, Typer, pytest, ruff, Docker Compose, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-16-rootcause-agent-design.md`

## Global Constraints

- Python `>=3.12`; dependências com piso de versão e `uv.lock` versionado.
- Todo código em `src/` (`src/rootcause`, `src/synthdata`, `src/evals`, `src/deploy`); testes em `tests/` espelhando `src/`.
- `domain/` não importa nada do projeto; `application/` só importa `domain/` e `application/ports.py`.
- Única dependência no host: Docker. `make up | seed | eval | test | lint | down` rodam em contêiner.
- LLM padrão: `ollama/qwen2.5:3b` em `OLLAMA_BASE_URL` (padrão `http://host.docker.internal:11434`); OpenAI/Anthropic só se a chave existir no `.env`.
- Dados 100% sintéticos; README diz "synthetic data in SAP table format, fictional manufacturer". Nada sobre Michelin, pneu, ou experiência real com SAP.
- Git: repositório novo, branch de trabalho `develop`; nunca commit/merge/push em `main`. Mensagens de commit sem qualquer identificação de IA (sem `Co-Authored-By`).
- Não subir para GitHub sem pedido explícito do Oséias. Sem deploy na AWS (decisão de 2026-11-16).
- Textos de dados (reclamações, notas de manutenção) em português de chão de fábrica; README principal em inglês + `README.pt-BR.md`.

## Review Focus

1. Reclamação sem número de entrega ou com número inexistente → o agente acha a entrega por cliente + material nos 90 dias antes da reclamação; sem nenhuma, `verdict="insufficient_data"`, nunca inventa id. (Task 3, Task 7)
2. LLM pequeno devolve JSON inválido, ferramenta inexistente ou argumento com tipo errado → erro volta como mensagem, passo conta no limite, sem exceção na API. (Task 6)
3. Relatório final cita `record_id` que não existe → `finalize` remove o id, baixa `confidence` e registra em `open_questions`. (Task 7)
4. Ollama fora do ar ou lento → Router tenta o próximo provedor configurado; se não houver, API devolve 503 com mensagem clara, não 500. (Task 10)
5. Revisão chamada duas vezes ou num id inexistente → 409 / 404, estado do grafo intacto. (Task 10)

---

### Task 1: Base do repositório e Docker

**Files:**
- Create: `pyproject.toml`, `uv.lock`, `.python-version`, `.gitignore`, `.dockerignore`, `.editorconfig`, `.env.example`, `Makefile`, `src/rootcause/__init__.py`, `src/rootcause/config.py`, `src/deploy/Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `tests/unit/test_config.py`
- Create: `src/synthdata/__init__.py`, `src/evals/__init__.py`

**Interfaces:**
- Produces: `Settings` (pydantic-settings) com `database_url: str`, `redis_url: str | None`, `llm_models: list[str]` (env `LLM_MODELS`, separado por vírgula, padrão `["ollama/qwen2.5:3b"]`), `ollama_base_url: str`, `max_steps: int = 8`, `embed_model: str = "intfloat/multilingual-e5-small"`, `langfuse_enabled: bool = False`; `get_settings() -> Settings` (cache).

- [ ] **Step 1:** `git init -b develop` em `~/workspace/workspace_think/rootcause-agent`; conferir `df -h /` (parar se < 20 GB).
- [ ] **Step 2: Teste** `test_settings_reads_llm_models_list`: com env `LLM_MODELS="ollama/qwen2.5:3b,openai/gpt-4o-mini"`, `get_settings().llm_models == ["ollama/qwen2.5:3b", "openai/gpt-4o-mini"]`; `test_defaults`: `max_steps == 8`.
- [ ] **Step 3:** Implementar `config.py`. `pyproject` com pacotes `rootcause`, `synthdata`, `evals` em `src/`, script `rootcause = "rootcause.cli:app"`, extras `dev` (pytest, ruff), torch CPU via índice `https://download.pytorch.org/whl/cpu` no `[tool.uv]`.
- [ ] **Step 4:** Dockerfile multi-stage (`python:3.12-slim`, uv, usuário `app` sem root, `HEALTHCHECK` em `/health`). Compose: `db` (`pgvector/pgvector:pg16`, volume, healthcheck `pg_isready`), `api`, `seed` (perfil `tools`), `redis` (`redis:7-alpine`), `ollama` (perfil `local-llm`), `extra_hosts: host.docker.internal:host-gateway`. Langfuse entra na Task 10.
- [ ] **Step 5:** Makefile: `up`, `down`, `seed`, `eval`, `test` (`docker compose run --rm api pytest`), `lint`, `shell`; cada alvo com `## descrição`.
- [ ] **Step 6:** CI: jobs `lint` (ruff), `test` (pytest com service `pgvector/pgvector:pg16`), `docker-build`.
- [ ] **Step 7: Verificar:** `make test` → testes passam dentro do contêiner; `docker compose up -d db` → healthy.
- [ ] **Step 8: Commit** `chore: base do projeto, Docker e CI`.

### Task 2: Domínio e portas

**Files:**
- Create: `src/rootcause/domain/models.py`, `src/rootcause/domain/records.py`, `src/rootcause/application/ports.py`
- Test: `tests/unit/domain/test_models.py`, `tests/unit/domain/test_records.py`

**Interfaces:**
- Produces (Pydantic, `frozen=True`):
  - `FailureMode(StrEnum)`: `bearing_wear, heater_drift, mold_wear, misalignment, sensor_fault`
  - `Verdict(StrEnum)`: `factory_cause, no_factory_cause, insufficient_data`
  - `Case(case_id, account_id, kunnr, created_on: date, matnr: str | None, vbeln: str | None, text)`
  - `Delivery(vbeln, posnr, matnr, charg, kunnr, delivered_on: date)`
  - `BatchOrigin(charg, aufnr, arbpl, equnr, start: datetime, end: datetime)`
  - `MaintenanceEvent(record_id, equnr, on: date, kind: Literal["note", "order"], text)`
  - `ManualPassage(record_id, page: int, text, score: float)`
  - `RootCauseReport(case_id, verdict, equnr: str | None, failure_mode: FailureMode | None, window_start: date | None, window_end: date | None, evidence: list[str], confidence: float (0..1), summary: str, open_questions: list[str])`
  - `records.make_id(table: str, *keys: str) -> str` → `"LIPS:80001234/000010"`; `records.parse_id(rid) -> tuple[str, tuple[str, ...]]`; tabelas válidas: `Case, KNA1, MARA, LIKP, LIPS, AFKO, AFPO, EQUI, QMEL, AUFK, MANUAL`.
- Produces (`typing.Protocol` em `ports.py`):
  - `CrmPort.get_case(case_id) -> Case | None`; `CrmPort.list_case_ids() -> list[str]`
  - `ErpPort.get_delivery(vbeln) -> list[Delivery]`; `ErpPort.find_deliveries(kunnr, matnr: str | None, since: date, until: date) -> list[Delivery]`; `ErpPort.get_batch_origin(charg) -> BatchOrigin | None`; `ErpPort.get_equipment_history(equnr, start: date, end: date) -> list[MaintenanceEvent]`; `ErpPort.record_exists(record_id) -> bool`
  - `ManualsPort.search(query, k: int = 4) -> list[ManualPassage]`

- [ ] **Step 1: Testes:** `test_report_rejects_confidence_above_1`; `test_factory_cause_requires_equnr_and_mode` (validator: `verdict=factory_cause` sem `equnr` → `ValidationError`); `test_make_and_parse_id_roundtrip` (`parse_id(make_id("LIPS","80001234","000010")) == ("LIPS", ("80001234","000010"))`); `test_parse_id_rejects_unknown_table`.
- [ ] **Step 2:** Rodar, ver falhar. **Step 3:** Implementar. **Step 4:** Rodar, ver passar.
- [ ] **Step 5:** Teste de arquitetura `tests/unit/test_layers.py::test_domain_imports_nothing_internal` (varre `import` em `domain/` e `application/` com `ast`).
- [ ] **Step 6: Commit** `feat: domínio e portas`.

### Task 3: Gerador de dados sintéticos e gabarito

**Files:**
- Create: `src/synthdata/schema.sql`, `src/synthdata/generator.py`, `src/synthdata/texts.py`, `src/synthdata/load.py`, `src/synthdata/__main__.py`
- Test: `tests/unit/synthdata/test_generator.py`, `tests/integration/test_load.py`

**Interfaces:**
- Consumes: `FailureMode`, `Verdict`, `make_id` (Task 2).
- Produces: `GroundTruth(case_id, verdict, equnr | None, failure_mode | None, window_start | None, window_end | None)`; `Dataset(tables: dict[str, list[dict]], truth: list[GroundTruth])`; `generate(seed: int = 7, n_fault_cases: int = 30, n_noise_cases: int = 10) -> Dataset`; `load(conn, ds: Dataset) -> None` (cria schema, trunca, insere; grava `truth` na tabela `eval_truth`); `python -m synthdata --seed 7`.

Cenário que o gerador precisa seguir (decide o que o agente consegue achar):
- 1 planta, 6 equipamentos (`EQUI`, ex.: `PR-01..PR-04` prensas, `EX-01..EX-02` extrusoras), 12 materiais, 40 clientes, 26 semanas.
- Manutenção de rotina em todos os equipamentos (lubrificação, inspeção) com texto normal: impede a regra "teve manutenção = defeito".
- 30 casos de falha vindos de ~8 episódios de falha: cada episódio tem equipamento, modo de falha, janela de 7 a 21 dias; notas `QMEL` na janela com sintomas em texto abreviado e ambíguo no começo ("ruido anormal mancal lado acion.", "temp. placa sup oscilando"); uma `AUFK` no fim da janela com o reparo. Lotes (`AFPO.charg`) produzidos no equipamento na janela vão para entregas; reclamações 14 a 42 dias após a entrega.
- 30% dos casos de falha sem `vbeln` ou com `vbeln` digitado errado (o agente precisa usar `find_deliveries`).
- 10 casos de ruído: lote de janela saudável; texto que culpa transporte/armazenagem/uso; gabarito `no_factory_cause`.
- Determinístico para a mesma semente.

- [ ] **Step 1: Testes:** `test_same_seed_same_dataset`; `test_counts` (`len(truth)==40`, 30 `factory_cause`); `test_every_fault_case_traces_to_equipment` (seguindo `LIPS.charg → AFPO → AFKO.arbpl → EQUI` chega no `truth.equnr`, e a produção cai dentro da janela); `test_noise_batches_outside_fault_windows`; `test_routine_maintenance_on_all_equipment`; `test_some_cases_missing_or_wrong_vbeln` (entre 6 e 12).
- [ ] **Step 2:** Rodar, ver falhar. **Step 3:** Implementar. **Step 4:** Rodar, ver passar.
- [ ] **Step 5: Integração** `test_load_roundtrip` (marcada `integration`, usa `DATABASE_URL`): `load` e depois `SELECT count(*) FROM eval_truth == 40`.
- [ ] **Step 6:** Serviço `seed` do compose roda `python -m synthdata` e depois o índice dos manuais (Task 5). `make seed` funciona.
- [ ] **Step 7: Commit** `feat: dados sintéticos no formato SAP e gabarito`.

### Task 4: Adaptadores ERP e CRM (Postgres)

**Files:**
- Create: `src/rootcause/adapters/erp/postgres.py`, `src/rootcause/adapters/crm/postgres.py`, `src/rootcause/adapters/db.py`
- Test: `tests/integration/test_erp_crm.py`, `tests/fakes.py`

**Interfaces:**
- Consumes: portas (Task 2), `load`/`generate` (Task 3).
- Produces: `PostgresErp(conn) : ErpPort`, `PostgresCrm(conn) : CrmPort`, `connect(url) -> psycopg.Connection`; `tests/fakes.py`: `InMemoryErp(ds: Dataset)`, `InMemoryCrm(ds)` implementando as mesmas portas para testes unitários.

- [ ] **Step 1: Testes** (parametrizados sobre `[InMemory*, Postgres*]`): `test_get_delivery_unknown_returns_empty`; `test_find_deliveries_window` (só entregas do cliente entre `since` e `until`); `test_batch_origin_matches_truth` para 3 casos; `test_history_filters_by_date`; `test_record_exists_true_and_false` (`"QMEL:999999999"` → False).
- [ ] **Step 2–4:** falhar, implementar com SQL parametrizado (nunca f-string), passar.
- [ ] **Step 5: Commit** `feat: adaptadores ERP e CRM`.

### Task 5: Busca nos manuais (pgvector)

**Files:**
- Create: `src/rootcause/adapters/manuals/pgvector.py`, `src/rootcause/adapters/manuals/ingest.py`
- Test: `tests/unit/manuals/test_chunking.py`, `tests/integration/test_manuals.py`

**Interfaces:**
- Produces: `chunk_pages(pages: list[str], size: int = 800, overlap: int = 150) -> list[tuple[int, str]]`; `ingest(conn, pdf_path, embedder) -> int`; `PgVectorManuals(conn, embedder) : ManualsPort`; `Embedder.encode(texts: list[str], kind: Literal["query", "passage"]) -> list[list[float]]` (prefixos `query: ` / `passage: ` do e5); record id `MANUAL:<page>:<n>`.
- PDF: baixar de `https://static.weg.net/medias/downloadcenter/ha6/h39/WEG-WMO-safe-area-50033244-manual-pt-en-es.pdf` para `data/manual.pdf` se não existir; `data/` fora do git.

- [ ] **Step 1: Testes:** `test_chunk_overlap` (dois trechos seguidos compartilham 150 caracteres); `test_chunk_keeps_page_number`; integração `test_search_returns_k_with_page` com embedder falso determinístico.
- [ ] **Step 2–4:** falhar, implementar (tabela `manual_chunks(record_id, page, text, embedding vector(384))`, índice HNSW cosseno), passar.
- [ ] **Step 5: Commit** `feat: busca nos manuais com pgvector`.

### Task 6: Gateway de LLM e ferramentas validadas

**Files:**
- Create: `src/rootcause/adapters/llm/gateway.py`, `src/rootcause/tools/registry.py`, `src/rootcause/tools/specs.py`
- Test: `tests/unit/tools/test_registry.py`, `tests/unit/llm/test_gateway.py`

**Interfaces:**
- Consumes: portas (Task 2).
- Produces:
  - `ToolCall(id, name, arguments: str)`; `ChatResult(content: str | None, tool_calls: list[ToolCall], tokens: int, model: str)`
  - `LlmClient(models: list[str], ...)`: `chat(messages: list[dict], tools: list[dict] | None = None, response_format: type[BaseModel] | None = None) -> ChatResult`; usa `litellm.Router` com `fallbacks` na ordem de `models`; levanta `LlmUnavailable` quando todos falham.
  - `ToolRegistry(erp, crm, manuals)`: `schemas() -> list[dict]` (formato OpenAI tools); `execute(call: ToolCall) -> ToolResult(record_ids: list[str], content: str, error: str | None)`.
  - Ferramentas: `get_case(case_id)`, `get_delivery(vbeln)`, `find_deliveries(kunnr, matnr?, since, until)`, `get_batch_origin(charg)`, `get_equipment_history(equnr, start, end)` (janela máx. 60 dias), `search_manuals(query)`. Args como modelos Pydantic; saída em JSON compacto com os `record_id`.

- [ ] **Step 1: Testes:** `test_unknown_tool_returns_error`; `test_invalid_json_returns_error`; `test_wrong_type_returns_error_with_field_name`; `test_history_window_over_60_days_rejected`; `test_result_lists_record_ids`; `test_gateway_falls_back_to_second_model` (mock `litellm` com primeiro modelo levantando erro); `test_gateway_raises_unavailable_when_all_fail`.
- [ ] **Step 2–4:** falhar, implementar, passar.
- [ ] **Step 5: Commit** `feat: gateway de LLM com fallback e ferramentas validadas`.

### Task 7: Pipeline fixo (linha de base) e finalização comum

**Files:**
- Create: `src/rootcause/application/finalize.py`, `src/rootcause/application/fixed.py`, `src/rootcause/agent/prompts/report.md`
- Test: `tests/unit/application/test_finalize.py`, `tests/unit/application/test_fixed.py`, `tests/fakes.py` (adicionar `ScriptedLlm`)

**Interfaces:**
- Consumes: portas, `LlmClient`, `ToolRegistry`.
- Produces: `finalize(draft: RootCauseReport, erp: ErpPort, seen_ids: set[str]) -> RootCauseReport` (remove ids que não existem ou que não foram vistos, multiplica `confidence` por 0.5 se removeu algo e anota em `open_questions`; `factory_cause` sem evidência restante vira `insufficient_data`); `investigate_fixed(case_id, crm, erp, manuals, llm) -> tuple[RootCauseReport, RunStats(steps: int, tokens: int)]`.
- Caminho fixo: caso → entrega (`vbeln` ou `find_deliveries` 90 dias antes) → lote → origem → histórico do equipamento de `start-14d` a `end+14d` → `search_manuals` com o texto das notas → uma chamada ao LLM com `response_format=RootCauseReport` → `finalize`.

- [ ] **Step 1: Testes:** `test_finalize_drops_unknown_ids_and_lowers_confidence`; `test_finalize_downgrades_factory_cause_without_evidence`; `test_fixed_finds_delivery_when_vbeln_missing`; `test_fixed_returns_insufficient_data_when_no_delivery` (sem chamar o LLM); `test_fixed_passes_history_to_llm` (`ScriptedLlm` recebe as notas da janela).
- [ ] **Step 2–4:** falhar, implementar, passar.
- [ ] **Step 5: Commit** `feat: pipeline fixo e finalização com checagem de evidência`.

### Task 8: Agente LangGraph com revisão humana

**Files:**
- Create: `src/rootcause/agent/graph.py`, `src/rootcause/agent/state.py`, `src/rootcause/agent/prompts/system.md`, `src/rootcause/adapters/tracing/steplog.py`
- Test: `tests/unit/agent/test_graph.py`

**Interfaces:**
- Consumes: `LlmClient`, `ToolRegistry`, `finalize`.
- Produces: `AgentState(TypedDict)`: `case_id, messages, seen_ids: list[str], steps: int, tokens: int, report: RootCauseReport | None, review: dict | None`; `build_graph(llm, tools, erp, checkpointer, max_steps: int) -> CompiledGraph`; nós `llm → tools → llm ...`, `finalize` (chamada com `response_format`) quando o modelo para de pedir ferramentas ou `steps == max_steps`, depois `review` com `interrupt({"report": ...})`; ao retomar com `{"decision": "approve" | "reject" | "edit", "report"?: ...}` grava `review`. Chamada idêntica repetida (mesmo nome + argumentos) não executa: devolve erro "repeated call". `steplog.log_step(thread_id, kind, payload)` escreve JSONL em stdout.
- `run_agent(case_id, ...) -> tuple[RootCauseReport, RunStats]` para avaliação: mesmo grafo com `review` desligado.

- [ ] **Step 1: Testes** (com `ScriptedLlm` e fakes em memória, `MemorySaver`): `test_agent_follows_tool_calls_and_finalizes`; `test_agent_stops_at_max_steps`; `test_repeated_call_not_executed`; `test_interrupt_then_approve_sets_review`; `test_invalid_tool_args_do_not_crash`.
- [ ] **Step 2–4:** falhar, implementar, passar.
- [ ] **Step 5: Commit** `feat: agente LangGraph com ferramentas e revisão humana`.

### Task 9: Avaliação e CLI

**Files:**
- Create: `src/evals/score.py`, `src/evals/runner.py`, `src/rootcause/composition.py`, `src/rootcause/cli.py`
- Test: `tests/unit/evals/test_score.py`

**Interfaces:**
- Consumes: `GroundTruth`, `investigate_fixed`, `run_agent`.
- Produces: `CaseScore(case_id, verdict_ok, equnr_ok, mode_ok, evidence_valid, steps, tokens)`; `score(report, truth, erp) -> CaseScore` (`evidence_valid`: todos os ids existem e, para `factory_cause`, pelo menos um é `QMEL`/`AUFK` do `truth.equnr` dentro da janela); `run(strategy: Literal["agent", "fixed"], model: str, limit: int | None) -> list[CaseScore]`; `summarize(scores) -> dict` com `verdict_acc, equnr_acc, mode_acc, evidence_valid_rate, noise_correct, mean_steps, mean_tokens`; grava `results/eval-<strategy>-<model>.json` e acrescenta linha em `results/README.md`.
- `composition.build(settings) -> Deps(crm, erp, manuals, llm, tools)`. CLI Typer: `rootcause investigate <case_id> [--strategy agent|fixed]`, `rootcause eval --strategy --model --limit`.

- [ ] **Step 1: Testes:** `test_score_correct_factory_case`; `test_score_noise_case_correct_when_no_factory_cause`; `test_evidence_invalid_when_id_missing`; `test_summarize_rates`.
- [ ] **Step 2–4:** falhar, implementar, passar.
- [ ] **Step 5: Rodar de verdade:** `make seed && make eval` com `qwen2.5:3b` nas duas estratégias (`--limit 10` primeiro para medir o tempo em CPU; depois os 40). Guardar os números reais em `results/`; não arredondar a favor do agente.
- [ ] **Step 6: Commit** `feat: avaliação agente contra pipeline fixo` (com `results/`).

### Task 10: API, cache e observabilidade

**Files:**
- Create: `src/rootcause/api/app.py`, `src/rootcause/api/schemas.py`, `src/deploy/langfuse.compose.yml` (incluído no compose com perfil `observability`)
- Modify: `docker-compose.yml`, `src/rootcause/adapters/llm/gateway.py` (cache Redis e callback Langfuse por config)
- Test: `tests/unit/api/test_app.py`

**Interfaces:**
- Consumes: `build_graph`, `composition.build`, checkpointer `PostgresSaver`.
- Produces: `GET /health` → `{"status": "ok"}`; `POST /investigations {case_id, strategy="agent"}` → `201 {thread_id, status: "pending_review", report}`; `GET /investigations/{thread_id}`; `POST /investigations/{thread_id}/review {decision, report?}` → `200 {status: "approved" | "rejected" | "edited", report}`; erros: caso inexistente 404, revisão repetida 409, `LlmUnavailable` 503.
- Langfuse v3 (web, worker, clickhouse, minio, postgres próprio) só no perfil `observability`; `LANGFUSE_*` no `.env.example`.

- [ ] **Step 1: Testes** (TestClient, deps falsas, `MemorySaver`): `test_health`; `test_create_returns_pending_review`; `test_unknown_case_404`; `test_review_twice_409`; `test_llm_unavailable_503`.
- [ ] **Step 2–4:** falhar, implementar, passar.
- [ ] **Step 5: Verificar:** `docker compose up -d` e `curl` no fluxo criar → revisar; com `--profile observability`, o trace aparece no Langfuse em `localhost:3000`. Conferir disco antes do perfil (`df -h /`).
- [ ] **Step 6: Commit** `feat: API com revisão humana, cache Redis e Langfuse`.

### Task 11: Marca e README

**Files:**
- Create: `assets/identidade/{svg/*, README.md}`, `README.md`, `README.pt-BR.md`, `docs/arquitetura.md`, `docs/dados-sinteticos.md`, `docs/avaliacao.md`, `docs/adr/0001-langgraph-com-nos-proprios.md`, `docs/adr/0002-pgvector-em-vez-de-chroma.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE` (MIT), `AGENTS.md`, `INDEX.yaml`, `.github/{ISSUE_TEMPLATE/*, pull_request_template.md, CODEOWNERS, dependabot.yml}`

- [ ] **Step 1: Pausa com o Oséias:** mostrar 2 a 3 opções de nome + emblema renderizados (arquivo ou artifact) e esperar a escolha. Renomear o pacote se o nome mudar.
- [ ] **Step 2:** Marca no padrão do ws_doctorate: emblema cor/mono/inverso, marca compacta, favicon, banner claro/escuro; guia com conceito, paleta, fontes, tamanhos mínimos.
- [ ] **Step 3:** README: `<picture>` claro/escuro, título, subtítulo, 4 a 5 badges (CI, Python, license, status, synthetic data), links, bloco "demo moment" de 5 linhas, problema, diagrama mermaid das camadas, **tabela com os números reais da Task 9**, quick start (`make up && make seed && make eval`), estrutura, decisões, limitações (dados sintéticos, modelo de 3B, sem deploy em nuvem).
- [ ] **Step 4: Verificar:** todos os links relativos abrem (script simples ou `lychee` via Docker); `make lint test` verde.
- [ ] **Step 5: Commit** `docs: marca, README e documentação`.
