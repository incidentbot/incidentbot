# How to contribute

## Development setup

Use Python 3.14.5 and [Poetry](https://python-poetry.org/) to install dependencies:

```sh
poetry install
```

## Validation

Run Ruff and the test suite before requesting review:

```sh
make lint
export IS_TEST_ENVIRONMENT=true
export POSTGRES_DB=incidentbot_test
export POSTGRES_HOST=localhost
export POSTGRES_PASSWORD=pytest
export POSTGRES_PORT=5432
export POSTGRES_USER=postgres
poetry run pytest tests/ -q
```

These database values are test placeholders. The suite uses in-memory SQLite fixtures and mocked integration clients; do not supply production credentials. `make tests` runs the same suite with verbose output.

Use four spaces for indentation. `make format` runs Ruff's formatter; review its diff and keep unrelated formatting out of the PR.

Pull requests run lint and tests. Image builds and publishing run after pushes to `main` or release tags. For changes to the Dockerfile or dependency installation, also validate a local image build:

```sh
docker build --target app --build-arg APP_VERSION=dev -t incidentbot:dev .
```

## Submitting changes

Open a pull request and fill out its template. Link the related issue and describe the resulting behavior, relevant validation, and any configuration changes. Update documentation beside the feature it describes; keep unrelated cleanup separate.

Feature and bugfix branches do not need release naming. Releases use CalVer tags in `YYYY.MM.DD` format; coordinate release tags with the maintainers rather than bumping versions in each fix.
