# How to contribute

Please review the following guidelines before contributing.

## Testing

Tests are encouraged when practical. All pull requests will run tests and test for successful Docker builds.

## Submitting changes

Please use the branch naming format `v0.0.0` - the branch name should simply be the version you are creating.

Please use semantic versioning for determining the next version number.

Please title the pull request `Release v0.0.0 - Title`. For example: `Release v1.2.3 - New feature doing this cool thing.`

Open a pull request with your proposed changes.

Please fill out the pull request template and use a list to describe your changes.

## Coding conventions

  * Indent using 4 spaces
  * Format using `black`

## Linting

Linting is done using `ruff`. If you've already used `poetry shell`, just run `make lint`.

Linting will occur on all pull requests and will fail if there are errors.
