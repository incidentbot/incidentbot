VENV := .venv

run:
	./$(VENV)/bin/python3 main.py

test-exec:
	./$(VENV)/bin/python3 test.py

init-db-schema:
	./$(VENV)/bin/alembic revision --autogenerate -m "Initial commit"

run-migrations:
	./$(VENV)/bin/alembic upgrade head

clean:
	rm -rf $(VENV)
	find . -type f -name '*.pyc' -delete

tests:
	./$(VENV)/bin/python -m pytest -v tests/

.PHONY: run test-exec init-db-schema run-migrations clean tests
