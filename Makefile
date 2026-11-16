.PHONY: help build up observability down seed eval investigate test test-int lint shell
.DEFAULT_GOAL := help
RUN = docker compose run --rm api

help:  ## lista os comandos
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-10s %s\n", $$1, $$2}'

build:  ## constrói a imagem da aplicação
	docker compose build api

up:  ## sobe banco, Redis e API
	docker compose up -d db redis api

observability:  ## sobe o Langfuse em http://localhost:3000
	docker compose --profile observability up -d

down:  ## para tudo (os volumes ficam)
	docker compose --profile observability --profile tools down

seed:  ## gera os dados sintéticos e indexa os manuais
	docker compose --profile tools run --rm seed

eval:  ## mede agente e pipeline fixo: make eval ARGS="--strategy agent --limit 10"
	docker compose --profile tools run --rm cli eval $(ARGS)

test:  ## testes unitários no contêiner
	$(RUN) pytest

test-int:  ## testes de integração (precisa do banco)
	$(RUN) pytest -m integration

lint:  ## confere o estilo
	$(RUN) ruff check src tests
	$(RUN) ruff format --check src tests

investigate:  ## investiga um caso: make investigate CASE=CS-00001
	docker compose --profile tools run --rm cli investigate $(CASE) $(ARGS)

shell:  ## abre um shell no contêiner
	$(RUN) bash
