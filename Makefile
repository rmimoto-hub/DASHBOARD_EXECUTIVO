# =====================================================================
# dir-dashboard — KAMI CO.
# Painel de Gestao Executiva
#
# Uso:  make <alvo>     |     make help  para a lista completa
# =====================================================================

SHELL := /bin/bash

# O ambiente conda que carrega Python, Node e o cliente MySQL.
CONDA_ENV  := dir-dashboard-80
ACTIVATE   := source $$HOME/miniforge3/etc/profile.d/conda.sh && conda activate $(CONDA_ENV)

MYSQL_CNF  := $$HOME/mysql-data/my.cnf
DB_NAME    := dir_dashboard

BACKEND    := backend
FRONTEND   := frontend

.DEFAULT_GOAL := help
.PHONY: help install install-backend install-frontend dev dev-backend \
        dev-frontend db-create db-schema db-reset seed-fake security-check \
        build lint mysql-start mysql-stop status

## help: mostra esta lista
help:
	@echo "dir-dashboard — alvos disponiveis:"
	@echo
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /' | column -t -s ':'
	@echo

# ---------------------------------------------------------------------
# Instalacao
# ---------------------------------------------------------------------

## install: instala as dependencias de backend e frontend
install: install-backend install-frontend
	@echo
	@echo "Dependencias instaladas."
	@echo "Proximos passos:  make db-schema  &&  make seed-fake  &&  make dev"

## install-backend: instala as dependencias Python
install-backend:
	@echo "==> Backend (Python)"
	@$(ACTIVATE) && cd $(BACKEND) && pip install -r requirements.txt
	@if [ ! -f $(BACKEND)/.env ]; then \
	  cp $(BACKEND)/.env.example $(BACKEND)/.env; \
	  echo "    .env criado a partir do exemplo — revise a SECRET_KEY."; \
	fi

## install-frontend: instala as dependencias Node
install-frontend:
	@echo "==> Frontend (Node)"
	@$(ACTIVATE) && cd $(FRONTEND) && npm install
	@if [ ! -f $(FRONTEND)/.env.local ]; then \
	  cp $(FRONTEND)/.env.example $(FRONTEND)/.env.local; \
	  echo "    .env.local criado a partir do exemplo."; \
	fi

# ---------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------

## mysql-start: sobe o MySQL local
mysql-start:
	@$$HOME/mysql-data/mysql-start.sh

## mysql-stop: desliga o MySQL local
mysql-stop:
	@$$HOME/mysql-data/mysql-stop.sh

## db-create: cria o banco (se ainda nao existir)
db-create:
	@$(ACTIVATE) && mysql --defaults-file=$(MYSQL_CNF) -u root -e \
	  "CREATE DATABASE IF NOT EXISTS $(DB_NAME) \
	   CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
	@echo "Banco $(DB_NAME) pronto."

## db-schema: aplica database/schema.sql
db-schema: db-create
	@$(ACTIVATE) && mysql --defaults-file=$(MYSQL_CNF) -u root $(DB_NAME) \
	  < database/schema.sql
	@echo "Schema aplicado."

## db-reset: APAGA e recria o banco (pede confirmacao)
db-reset:
	@echo "ATENCAO: isso apaga TODOS os dados de $(DB_NAME)."
	@read -p "Digite 'confirmo' para prosseguir: " r; \
	 if [ "$$r" != "confirmo" ]; then echo "Cancelado."; exit 1; fi; \
	 $(ACTIVATE) && mysql --defaults-file=$(MYSQL_CNF) -u root -e \
	   "DROP DATABASE IF EXISTS $(DB_NAME);"
	@$(MAKE) --no-print-directory db-schema

## seed-fake: carrega dados ficticios para testes
seed-fake:
	@$(ACTIVATE) && cd $(BACKEND) && python -m scripts.seed_fake

# ---------------------------------------------------------------------
# Desenvolvimento
# ---------------------------------------------------------------------

## dev: sobe backend e frontend juntos
dev:
	@$(ACTIVATE) && \
	  trap 'kill 0' EXIT INT TERM; \
	  ( cd $(BACKEND)  && uvicorn app.main:app --reload --port 8000 ) & \
	  ( cd $(FRONTEND) && npm run dev ) & \
	  echo ""; \
	  echo "  Backend   http://localhost:8000    (docs: /docs)"; \
	  echo "  Frontend  http://localhost:3000"; \
	  echo "  Ctrl+C encerra os dois."; \
	  echo ""; \
	  wait

## dev-backend: sobe apenas o backend
dev-backend:
	@$(ACTIVATE) && cd $(BACKEND) && uvicorn app.main:app --reload --port 8000

## dev-frontend: sobe apenas o frontend
dev-frontend:
	@$(ACTIVATE) && cd $(FRONTEND) && npm run dev

## build: build de producao do frontend
build:
	@$(ACTIVATE) && cd $(FRONTEND) && npm run build

## lint: roda o linter do frontend
lint:
	@$(ACTIVATE) && cd $(FRONTEND) && npm run lint

## status: mostra o estado do ambiente
status:
	@$(ACTIVATE) && \
	  echo "Python   $$(python --version 2>&1)" && \
	  echo "Node     $$(node --version)" && \
	  echo "MySQL    $$(mysql --version | sed 's/.*Ver //;s/ .*//')" && \
	  printf "MySQL up " && \
	  (mysqladmin --defaults-file=$(MYSQL_CNF) -u root ping 2>/dev/null \
	    || echo "NAO — rode: make mysql-start")

# ---------------------------------------------------------------------
# Seguranca
# ---------------------------------------------------------------------

## security-check: verificacao obrigatoria antes de subir para o GitHub
security-check:
	@$(ACTIVATE) && bash scripts/security_check.sh
