VENV := .venv

clean:
	rm -rf $(VENV)
	find . -type f -name '*.pyc' -delete

generate-client:
	./scripts/generate-client.sh

init-db-schema: shell
	./$(VENV)/bin/alembic revision --autogenerate -m "Initial commit"

lint:
	ruff check --verbose

run-migrations: shell
	./$(VENV)/bin/alembic upgrade head

run: shell
	./$(VENV)/bin/python3 main.py

setup:
	poetry install --no-root

shell:
	poetry shell

test-exec:
	./$(VENV)/bin/python3 test.py

tests:
	./$(VENV)/bin/python -m pytest -v tests/

update: shell
	poetry update

.PHONY: clean generate-client init-db-schema lint run-migrations run-server setup shell test-exec tests update
