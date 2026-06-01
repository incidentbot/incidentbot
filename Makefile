SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := help

.PHONY: help clean bootstrap setup update run shell \
        db-bootstrap-local init-db-schema migrations \
        ci lint format check-deps tests generate-openapi-client \
        coverage coverage-report coverage-gaps \
        up down restart logs build build-all \
        venv-path doctor vscode-interpreter vscode-settings-line

# Set PLAIN=1 to suppress color (e.g. for piping: make help PLAIN=1)
PLAIN ?= 0

help: ## Show this help
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk -v plain="$(PLAIN)" \
		    'BEGIN{FS=":.*?## "} \
		     {if (plain=="1") printf "%-26s %s\n", $$1, $$2; \
		      else            printf "\033[36m%-26s\033[0m %s\n", $$1, $$2}'

clean: ## Remove caches / compiled files (safe even without .venv)
	@rm -rf .venv
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +

# ---------------------------------------------------------------------------
# Bootstrap / Environment
# ---------------------------------------------------------------------------

PY_VERSION_FILE ?= .python-version

# Internal: configure Poetry to use an in-project .venv
ensure-poetry-config:
	@set -e; \
	cur_inproj="$$(poetry config virtualenvs.in-project --local 2>/dev/null || echo unset)"; \
	if [ "$$cur_inproj" != "true" ]; then \
		echo "🔧  enabling in-project venv (virtualenvs.in-project=true)"; \
		poetry config virtualenvs.in-project true --local; \
	fi; \
	if poetry config virtualenvs.prefer-active-python --local >/dev/null 2>&1; then \
		cur_prefpy="$$(poetry config virtualenvs.prefer-active-python --local)"; \
		if [ "$$cur_prefpy" != "true" ]; then \
			echo "🔧  prefer active Python (virtualenvs.prefer-active-python=true)"; \
			poetry config virtualenvs.prefer-active-python true --local >/dev/null 2>&1 || true; \
		fi; \
	else \
		echo "ℹ️  poetry: virtualenvs.prefer-active-python not supported; skipping."; \
	fi

# Internal: install the pinned Python version via pyenv/asdf if .python-version exists
ensure-python:
	@set -e; \
	if [ -f "$(PY_VERSION_FILE)" ]; then \
		V="$$(tr -d ' \n' < "$(PY_VERSION_FILE)")"; \
		echo "🧰 using Python $$V from $(PY_VERSION_FILE)"; \
		if command -v pyenv >/dev/null 2>&1; then \
			echo "   (pyenv) ensuring $$V is installed..."; \
			pyenv install -s "$$V"; \
		fi; \
		if command -v asdf >/dev/null 2>&1; then \
			echo "   (asdf) ensuring $$V is installed..."; \
			asdf plugin add python >/dev/null 2>&1 || true; \
			asdf install python "$$V" || true; \
			asdf local python "$$V" || true; \
		fi; \
		echo "   telling Poetry to use $$V"; \
		poetry env use "$$V"; \
	fi

# Internal: create .venv + install deps if the venv doesn't exist yet
ensure-venv: ensure-poetry-config ensure-python
	@set -e; \
	VP="$$(poetry env info --path 2>/dev/null || true)"; \
	if [ -z "$$VP" ] || [ ! -d "$$VP" ]; then \
		echo "🐍 creating project venv and installing deps..."; \
		poetry install --no-root; \
	fi

bootstrap: ensure-venv ## One-shot: configure Poetry, pin Python version, create venv, install deps
	@true

setup: ## Install / sync project dependencies into existing venv
	@poetry install --no-root

update: ## Update all dependencies to latest versions and rewrite pyproject.toml constraints
	@poetry self show plugins 2>/dev/null | grep -q poetry-plugin-up || poetry self add poetry-plugin-up
	@poetry up --latest

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

run: ## Run the main application
	@poetry run python main.py

shell: ## Spawn an interactive Poetry shell
	@poetry shell

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Superuser credentials for db-bootstrap-local (psql PG* convention)
PGHOST           ?= localhost
PGPORT           ?= 5432
PGUSER           ?= postgres
PGPASSWORD       ?= postgres
PG_BOOTSTRAP_SQL ?= scripts/bootstrap_local_pg.sql

# App-level DB credentials used by Alembic (matches docker-compose.dev.yml defaults)
# Override any of these on the command line or via env vars for non-dev targets.
POSTGRES_HOST     ?= localhost
POSTGRES_PORT     ?= 5432
POSTGRES_USER     ?= incident_bot
POSTGRES_PASSWORD ?= somepassword
POSTGRES_DB       ?= incident_bot

db-bootstrap-local: ## Create local dev role+db on $(PGHOST):$(PGPORT) (role/db: incident_bot_dev)
	@command -v psql >/dev/null 2>&1 || { echo "❌ psql not found"; exit 1; }
	@[ -f "$(PG_BOOTSTRAP_SQL)" ] || { echo "❌ SQL file not found: $(PG_BOOTSTRAP_SQL)"; exit 1; }
	@echo "🔗 checking Postgres connection to $(PGHOST):$(PGPORT) as $(PGUSER)…"
	@PGHOST="$(PGHOST)" PGPORT="$(PGPORT)" PGUSER="$(PGUSER)" PGPASSWORD="$(PGPASSWORD)" \
	psql -X -d postgres -q -At -c "SELECT 1" >/dev/null || { \
		echo "❌ unable to connect (host=$(PGHOST) port=$(PGPORT) user=$(PGUSER))"; \
		exit 1; \
	}
	@echo "🚀 running bootstrap SQL from $(PG_BOOTSTRAP_SQL)…"
	@PGHOST="$(PGHOST)" PGPORT="$(PGPORT)" PGUSER="$(PGUSER)" PGPASSWORD="$(PGPASSWORD)" \
	psql -X -v ON_ERROR_STOP=1 -v PW="$(PGPASSWORD)" -d postgres -q -f "$(PG_BOOTSTRAP_SQL)"
	@echo "☑️  local postgres bootstrap complete"

init-db-schema: ## Autogenerate an Alembic revision (uses POSTGRES_* vars, defaults match make up)
	@POSTGRES_HOST=$(POSTGRES_HOST) \
	POSTGRES_PORT=$(POSTGRES_PORT) \
	POSTGRES_USER=$(POSTGRES_USER) \
	POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
	POSTGRES_DB=$(POSTGRES_DB) \
	poetry run alembic revision --autogenerate -m "Initial commit"

migrations: ## Apply Alembic migrations to head (uses POSTGRES_* vars, defaults match make up)
	@POSTGRES_HOST=$(POSTGRES_HOST) \
	POSTGRES_PORT=$(POSTGRES_PORT) \
	POSTGRES_USER=$(POSTGRES_USER) \
	POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
	POSTGRES_DB=$(POSTGRES_DB) \
	poetry run alembic upgrade head

# ---------------------------------------------------------------------------
# Code quality
# ---------------------------------------------------------------------------

ci: ## Mirror PR CI: lint then tests (matches GitHub Actions jobs exactly)
	@$(MAKE) lint
	@IS_TEST_ENVIRONMENT=true BOLT_PYTHON_MOCK_SERVER_MODE=threading \
		poetry run pytest tests/ -q

check-deps: ## Check for unused, missing, or transitive dependencies
	@poetry run deptry .

format: ## Format code with ruff (writes changes)
	@poetry run ruff format .

generate-openapi-client: ## Generate OpenAPI client assets
	@poetry run bash ./scripts/generate-openapi-client.sh

lint: ## Lint with ruff (check only, no writes)
	@poetry run ruff check

tests: ## Run the pytest suite
	@poetry run pytest -v tests/

# Minimum coverage % a file must reach before it is considered an "offender".
# Override on the command line: make coverage-gaps COVERAGE_MIN=90
COVERAGE_MIN ?= 80

coverage: ## Run tests with coverage (term-missing + HTML + XML reports)
	@IS_TEST_ENVIRONMENT=true BOLT_PYTHON_MOCK_SERVER_MODE=threading \
		poetry run pytest tests/ -q \
		--cov=incidentbot \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-report=xml
	@echo ""
	@echo "HTML report → htmlcov/index.html"
	@echo "XML  report → coverage.xml"

coverage-report: ## Print per-file coverage table (lowest first). Run 'make coverage' first.
	@poetry run coverage report --sort=cover --show-missing

coverage-gaps: ## List files below COVERAGE_MIN% (default 80). Run 'make coverage' first.
	@echo "Files below $(COVERAGE_MIN)% coverage:"
	@echo "─────────────────────────────────────────────────────────────────"
	@poetry run coverage report --sort=cover | \
		awk -v min=$(COVERAGE_MIN) \
		'NR==1{print; next} /^[-]+$$/{next} /TOTAL/{next} \
		 {pct=$$NF; sub(/%/,"",pct); if (pct+0 < min) print}'
	@echo "─────────────────────────────────────────────────────────────────"

# ---------------------------------------------------------------------------
# Docker — local dev stack
# ---------------------------------------------------------------------------

COMPOSE_FILE ?= docker-compose.dev.yml

up: ## Start local dev stack (db + bot), rebuilding the image if needed
	@docker compose -f $(COMPOSE_FILE) up -d --build

down: ## Stop and remove local dev stack containers
	@docker compose -f $(COMPOSE_FILE) down

restart: ## Restart the bot container (picks up code changes without a full rebuild)
	@docker compose -f $(COMPOSE_FILE) restart bot

logs: ## Tail bot logs
	@docker compose -f $(COMPOSE_FILE) logs -f bot

# ---------------------------------------------------------------------------
# Docker — image builds
# ---------------------------------------------------------------------------

# Image name for local builds — override to push to your own registry.
# In CI, images are pushed to ghcr.io/<org>/incidentbot automatically.
IMAGE_NAME ?= incidentbot
IMAGE_TAG  ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo dev)

build: ## Build app image for the local platform
	@docker buildx build \
		--target app \
		--build-arg APP_VERSION=$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		--load \
		.

build-all: ## Build app image for linux/amd64 + linux/arm64 (requires buildx)
	@docker buildx create --use --name incidentbot-builder 2>/dev/null || true
	@docker buildx build \
		--platform linux/amd64,linux/arm64 \
		--target app \
		--build-arg APP_VERSION=$(IMAGE_TAG) \
		--tag $(IMAGE_NAME):$(IMAGE_TAG) \
		.

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

doctor: ## Print env diagnostics (Python path, venv, sqlmodel version)
	@echo "Poetry venv: $$(poetry env info --path)"
	@echo "Python ver : $$(poetry run python -V)"
	@printf '%s\n' \
		'import sys, os' \
		'print("sys.executable:", sys.executable)' \
		'try:' \
		'    import sqlmodel' \
		'    print("sqlmodel version:", getattr(sqlmodel, "__version__", "unknown"))' \
		'except Exception as e:' \
		'    print("sqlmodel import error:", e)' \
	| poetry run python -

venv-path: ## Print the Poetry virtualenv path
	@poetry env info --path

vscode-interpreter: ## Print the full Python interpreter path (for VS Code)
	@set -e; \
	P="$$(poetry run python -c 'import sys; print(sys.executable)')"; \
	echo "$$P"

vscode-settings-line: ## Print the JSON snippet to set VS Code's Python interpreter
	@set -e; \
	P="$$(poetry run python -c 'import sys; print(sys.executable)')"; \
	echo "\"python.defaultInterpreterPath\": \"$$P\","
