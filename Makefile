SHELL := /bin/bash
.ONESHELL:
.DEFAULT_GOAL := help

.PHONY: help clean client generate-openapi-client init-db-schema lint migrations \
        server setup shell test-exec tests update worker venv-path doctor \
        ensure-poetry-config ensure-venv bootstrap readme ensure-python

# Color / no-color toggle for help output
PLAIN ?= 0

ifeq ($(PLAIN),1)
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "};{printf "%-22s %s\n", $$1, $$2}'
else
help: ## Show this help
	@grep -E '^[a-zA-Z0-9_.-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "};{printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'
endif

clean: ## Remove caches / compiled files (safe even without .venv)
	@rm -rf .venv
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -prune -exec rm -rf {} +

# Bootstrap / Env

PY_VERSION_FILE ?= .python-version

ensure-poetry-config: ## Ensure Poetry uses in-project .venv via local config
	@set -e; \
	cur_inproj="$$(poetry config virtualenvs.in-project --local 2>/dev/null || echo unset)"; \
	if [ "$$cur_inproj" != "true" ]; then \
		echo "🔧  enabling in-project venv (virtualenvs.in-project=true)"; \
		poetry config virtualenvs.in-project true --local; \
	fi; \
	if poetry config virtualenvs.prefer-active-python --local >/dev/null 2>&1; then \
		cur_prefpy="$$(poetry config virtualenvs.prefer-active-python --local)"; \
		if [ "$$cur_prefpy" != "true" ]; then \
			echo "🔧  prefer active Python for venv (virtualenvs.prefer-active-python=true)"; \
			poetry config virtualenvs.prefer-active-python true --local >/dev/null 2>&1 || true; \
		fi; \
	else \
		echo "ℹ️  poetry: virtualenvs.prefer-active-python not supported; skipping."; \
	fi

ensure-python: ## If .python-version exists, install (via pyenv/asdf) and select it for Poetry
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

ensure-venv: ensure-poetry-config ensure-python ## Create .venv if missing (after selecting python)
	@set -e; \
	VP="$$(poetry env info --path 2>/dev/null || true)"; \
	if [ -z "$$VP" ] || [ ! -d "$$VP" ]; then \
		echo "🐍 creating project venv and installing deps..."; \
		poetry install --no-root; \
	fi

bootstrap: ensure-venv ## One-shot: ensure config + python version + venv + deps
	@true

setup: ensure-venv ## Install project dependencies into Poetry's managed venv
	@poetry install --no-root

update: ## Update dependencies to latest allowed by pyproject.toml
	@poetry update

# App commands

run: ## Run main application
	@poetry run python main.py

# Database commands

# ---- Local Postgres bootstrap

.PHONY: db-bootstrap-local
PGHOST ?= localhost
PGPORT ?= 5432
PGUSER ?= postgres
PGPASSWORD ?= postgres
PG_BOOTSTRAP_SQL ?= scripts/bootstrap_local_pg.sql

db-bootstrap-local: ## Create local dev role+db on $(PGHOST):$(PGPORT) (role/db: incident_bot_dev, password: $(PGPASSWORD) [dev only])
	@# Safety checks
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

	@echo "☑️ local postgres bootstrap complete"

# ---- Alembic migrations

init-db-schema: ## Autogenerate an Alembic revision
	@poetry run alembic revision --autogenerate -m "Initial commit"

migrations: ## Apply migrations to head
	@poetry run alembic upgrade head

# Tooling

lint: ## Lint with ruff
	@poetry run ruff check

tests: ## Run pytest suite
	@poetry run pytest -v tests/

test-exec: ## Run a simple test script
	@poetry run python test.py

generate-openapi-client: ## Generate OpenAPI client assets
	@poetry run bash ./scripts/generate-openapi-client.sh

shell: ## Spawn an interactive Poetry shell
	@poetry shell

# Diagnostics

venv-path: ## Print Poetry virtualenv path
	@poetry env info --path

doctor: ## Print useful env diagnostics (Python, venv, sqlmodel presence)
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

# VS Code integration

.PHONY: vscode-interpreter vscode-settings-line

vscode-interpreter: ## Print the full Python interpreter path for VS Code
	@set -e; \
	P="$$(poetry run python -c 'import sys; print(sys.executable)')"; \
	echo "$$P"

vscode-settings-line: ## Print the JSON settings line for VS Code interpreter
	@set -e; \
	P="$$(poetry run python -c 'import sys; print(sys.executable)')"; \
	echo "\"python.defaultInterpreterPath\": \"$$P\","
