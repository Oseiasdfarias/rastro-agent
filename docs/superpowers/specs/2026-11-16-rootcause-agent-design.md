# Desenho: rootcause-agent (nome provisório)

Data: 2026-11-16 · Status: aguardando aprovação

## Intenção

Projeto público de portfólio que mostra um agente de IA "pronto para produção" na indústria:
recebe a reclamação de um cliente (CRM), segue o rastro nos dados do ERP no formato SAP até a
máquina e a manutenção, consulta manuais e entrega um relatório de causa provável, com fonte em
cada fato, para um engenheiro da qualidade revisar.

Por quê: processo seletivo de consultor de IA (ACT Digital, cliente Michelin). O tema conversa
com o que a Michelin divulga (diagnóstico de manutenção, causa raiz) sem falar de pneu. Também
serve de base para posts de LinkedIn para público não técnico (as camadas em volta do modelo).

## Objetivos

- Mostrar as camadas da imagem de referência: entrada validada, agente com ferramentas, troca de
  provedor, dados, registro de cada passo, testes, entrega.
- Ter um número medido: taxa de acerto da causa em casos de resposta conhecida.
- Responder "quando não usar agente": comparar com um pipeline fixo, sem agente.
- README e identidade visual no padrão do ws_doctorate.

## Fora do escopo

- Dados reais de SAP ou CRM, conector SAP de verdade (RFC, OData), interface web própria.
- Previsão de falha por sensor (isso é ML clássico, não LLM).

## Anti-objetivos (falha mesmo funcionando)

- Parecer chatbot de atendimento ao cliente: quem usa é a engenharia.
- Afirmar experiência com SAP, GCP ou com a Michelin. O README diz "dados sintéticos no formato
  de tabelas SAP" e "fabricante fictício".
- Demo bonita sem medição, ou gabarito escrito à mão sabendo a resposta.

## Restrições

- Tem que rodar local sem chave paga (Ollama). OpenAI/Anthropic opcionais via LiteLLM.
- CPU apenas na máquina dele; modelos locais pequenos (qwen2.5:3b ou 7b).
- Sem deploy em nuvem (decidido em 2026-11-16). Branch `develop`; nada direto em `main`.
- Commits sem identificação de IA.

## Abordagens consideradas

1. **Agente com ferramentas (LangGraph)**: o LLM decide a ordem das consultas; pausa nativa para
   revisão humana e checkpoint. Escolhida: é a pilha da imagem e a mais pedida em vagas.
2. **Pipeline fixo + LLM só para escrever o relatório**: joins determinísticos CRM → entrega →
   lote → ordem de produção → máquina → manutenção. Mais barato e previsível. Entra como
   **linha de base** na avaliação, não como produto.
3. **Loop escrito na mão, sem framework** (como o post W58b): didático, mas o projeto quer mostrar
   a pilha de mercado. Descartado.

## Estrutura

Todo código em `src/`; a raiz guarda repositório, docs, marca e CI.

```
src/rootcause/        domain/ application/ (portas) agent/ (+prompts/) tools/
                      adapters/{erp,crm,manuals,llm,tracing}/ api/ composition.py config.py cli.py
src/synthdata/        gerador com semente fixa e falhas plantadas
src/evals/            casos com causa conhecida, runner, métricas
src/deploy/           Dockerfile e arquivos do compose
tests/                espelha src/: unit/ integration/ evals/
data/                 gerado (fora do git), amostra pequena versionada
docs/ assets/identidade/ .github/  README.md README.pt-BR.md Makefile pyproject.toml ...
```

Regra de dependência: `domain` não importa nada; `application` só conhece portas; `adapters`
implementam; `composition.py` liga.

## Dados sintéticos

Tabelas no formato SAP, nomes reais de tabela e campos principais, em Postgres:

| Tabela | Conteúdo |
|---|---|
| KNA1 | clientes |
| MARA | materiais (produtos fictícios de borracha/metal industrial) |
| VBAK / VBAP | pedidos de venda (cabeçalho / item) |
| LIKP / LIPS | entregas, com lote (CHARG) por item |
| AFKO / AFPO | ordens de produção, com lote produzido e centro de trabalho |
| CRHD / EQUI | centros de trabalho e equipamentos (máquinas) |
| QMEL | notas de qualidade e de manutenção |
| AUFK | ordens de manutenção |

CRM (formato estilo Salesforce): `Account`, `Case` (reclamação com texto livre, produto, número
da entrega às vezes ausente ou errado).

O gerador planta N falhas com causa conhecida (ex.: rolamento da prensa PR-03 entre duas ordens
de manutenção, lotes dessa janela com defeito, reclamações 2 a 6 semanas depois) e ruído
(reclamações sem causa de fábrica, texto com abreviação e erro, entrega ausente). Cada falha
plantada vira um caso de avaliação com resposta certa em campos fechados.

## Fluxo do agente

1. Entrada (FastAPI + Pydantic): id do caso do CRM.
2. Ferramentas: `get_case`, `find_delivery`, `get_batch_origin`, `get_equipment_history`,
   `search_manuals` (manual WEG em pgvector, com as escolhas que mediram melhor no
   rag-manual-poc: e5-small, trechos 800/150; o rag-manual-poc usa Chroma, por isso não entra
   como biblioteca).
3. Cada chamada validada (schema, limite de passos, chamada repetida); erro volta ao modelo.
4. Saída estruturada: `RootCauseReport{equipment_id, failure_mode, window, evidence[record_id],
   confidence, open_questions}`. Todo `record_id` citado precisa existir (checado no código).
5. Pausa para revisão humana (aprovar, corrigir, rejeitar) antes de marcar o caso.

## Avaliação

- 30 casos das falhas plantadas + 10 de ruído (resposta certa: "sem causa de fábrica").
- Métricas: acerto de equipamento e modo de falha; evidência válida (ids existem e sustentam);
  recusa correta nos casos de ruído; passos e tokens por caso.
- Comparação: agente vs pipeline fixo, mesmos modelos. O resultado entra no README, qualquer que
  seja (se o pipeline fixo ganhar, isso vira a lição).

## Docker (decidido em 2026-11-16: projeto final, tudo em contêiner)

`docker compose up` sobe tudo; a única dependência no host é o Docker.

| Serviço | Imagem | Papel |
|---|---|---|
| `db` | pgvector/pgvector:pg16 | tabelas SAP/CRM sintéticas + checkpoints do LangGraph |
| `seed` | imagem da app | roda `synthdata` uma vez e indexa os manuais |
| `api` | imagem da app (multi-stage, python slim, usuário sem root, healthcheck) | FastAPI |
| `redis` | redis:7-alpine | cache de respostas do LLM e das ferramentas |
| `langfuse` + `clickhouse` + `minio` | oficiais | registro de cada passo; perfil `observability` |
| `ollama` | ollama/ollama | perfil `local-llm`; por padrão usa o Ollama do host (`host.docker.internal`) |

Perfis do compose deixam a pilha leve por padrão. `make up`, `make seed`, `make eval`,
`make test` rodam dentro dos contêineres. Testes de integração usam o mesmo compose na CI.
Disco: cerca de 5 a 6 GB de imagens; 26 GB livres em 2026-11-16.

## Ordem de construção

1. Base: pyproject (uv), Dockerfile, compose com `db`, CI, estrutura de `src/`.
2. synthdata + schema Postgres + casos de avaliação.
3. Domínio, portas, adaptadores ERP/CRM/manuais, ferramentas validadas.
4. Pipeline fixo (linha de base) e agente LangGraph com saída estruturada e checagem de ids.
5. Avaliação dos dois; número no README.
6. API FastAPI com revisão humana, Redis, LiteLLM com troca de provedor, Langfuse.
7. Marca e README final em inglês e português. Sem deploy na AWS (decidido em 2026-11-16).

## Decisões deixadas ao construtor

Nomes de campos além dos principais, volume de dados (alvo: milhares de linhas, gerado em
segundos), formato do log, escolha exata do modelo local por custo de CPU, estilo dos prompts.

## Pendente com o Oséias

- Nome e marca (opções desenhadas depois da aprovação).
- Data da entrevista da Michelin (define se a fase 1 precisa sair antes).
- Repositório público no GitHub: criar quando ele pedir.
