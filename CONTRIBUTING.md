# How to contribute

Please review the following guidelines before contributing.

## Development setup

This project uses [Poetry](https://python-poetry.org/) to manage dependencies.

```bash
poetry install
poetry shell
```

To run tests:

```bash
make test
# or directly:
poetry run pytest tests/ -q
```

## Testing

Tests are encouraged when practical. All pull requests will run tests and a Docker build check as part of CI.

## Submitting changes

Open a pull request with your proposed changes and fill out the pull request template.

**Release PRs** should follow this convention:
- Branch name: `v0.0.0` (just the version)
- PR title: `Release v0.0.0 - Title` (e.g. `Release v1.2.3 - Add Phare integration`)
- Use [semantic versioning](https://semver.org/) to determine the next version number

Feature and bugfix PRs don't need to follow the release naming convention.

## Coding conventions

- Indent using 4 spaces
- Format and lint using `ruff` — run `make lint` after activating the poetry shell

## Linting

Linting runs automatically on all pull requests via CI and will fail if there are errors. You can run it locally with:

```bash
make lint
```
