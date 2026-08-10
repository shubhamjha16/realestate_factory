.DEFAULT_GOAL := help
SHELL := /bin/bash

BACKEND  := backend
FRONTEND := frontend
UV       := uv --project $(BACKEND)
PY       := $(BACKEND)/.venv/bin/python

# `intake_node` joins a set to build its prompt, so an unpinned hash seed makes
# every run irreproducible. Pinned here and in CI until S10 makes prompts data.
export PYTHONHASHSEED := 0

.PHONY: help install install-backend install-frontend dev dev-backend dev-frontend \
        infra infra-down test test-backend test-frontend golden golden-record \
        lint typecheck migrate migration build clean

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── setup ─────────────────────────────────────────────────────────────────────

install: install-backend install-frontend ## Install both apps

install-backend: ## uv sync the backend (Python 3.12)
	$(UV) sync --all-groups

install-frontend: ## yarn install the console
	yarn install

# ── run ───────────────────────────────────────────────────────────────────────

infra: ## Start postgres+postgis and redis
	docker compose up -d
	@echo "postgres :5433  ·  redis :6380"

infra-down: ## Stop and remove the local containers
	docker compose down

dev: ## Bring up postgis, redis, the API and the console
	@$(MAKE) infra
	@trap 'kill 0' EXIT INT TERM; \
	  $(MAKE) dev-backend & \
	  $(MAKE) dev-frontend & \
	  wait

dev-backend: ## API only, with reload, on :8004
	cd $(BACKEND) && .venv/bin/uvicorn app.main:app --reload --port 8004

dev-frontend: ## Console only, on :5173
	yarn workspace realestate-factory-frontend dev

# ── verify ────────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run both suites

test-backend: ## pytest, including the golden set
	cd $(BACKEND) && .venv/bin/python -m pytest -q

test-frontend: ## vitest
	yarn workspace realestate-factory-frontend test

golden: ## Replay the golden set and diff against expected/
	cd $(BACKEND) && .venv/bin/python tests/golden/runner.py --target package --mode replay

golden-record: ## Re-record the golden set against the live provider (needs GROQ_API_KEY)
	@test -n "$$GROQ_API_KEY" || { echo "GROQ_API_KEY is not set"; exit 1; }
	cd $(BACKEND) && .venv/bin/python tests/golden/runner.py \
	  --target package --mode record --write-expected

lint: ## ruff + eslint
	cd $(BACKEND) && .venv/bin/ruff check .
	yarn workspace realestate-factory-frontend lint

typecheck: ## mypy + tsc
	cd $(BACKEND) && .venv/bin/mypy app
	yarn workspace realestate-factory-frontend typecheck

# ── database ──────────────────────────────────────────────────────────────────

migrate: ## alembic upgrade head
	cd $(BACKEND) && .venv/bin/alembic upgrade head

migration: ## Autogenerate a revision — then hand-review it (m="message")
	@test -n "$(m)" || { echo 'usage: make migration m="add properties"'; exit 1; }
	cd $(BACKEND) && .venv/bin/alembic revision --autogenerate -m "$(m)"
	@echo
	@echo "Hand-review before committing:"
	@echo "  · no monetary column typed Float — NUMERIC(18,2) only"
	@echo "  · GiST index hand-added for every geography column"
	@echo "  · downgrade() written and reversible"

# ── build ─────────────────────────────────────────────────────────────────────

build: ## Build the console and re-export requirements.txt
	yarn workspace realestate-factory-frontend build
	$(UV) export --no-hashes --no-dev --no-emit-project -o $(BACKEND)/requirements.txt

clean: ## Remove build output and caches
	rm -rf $(FRONTEND)/dist $(FRONTEND)/node_modules/.vite
	find $(BACKEND) -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf $(BACKEND)/.pytest_cache $(BACKEND)/.ruff_cache $(BACKEND)/.mypy_cache
