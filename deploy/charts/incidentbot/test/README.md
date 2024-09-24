# Incident Bot Helm Chart Unit Testing

[bats](https://github.com/bats-core/bats-core) is used to run unit tests against this Helm chart.

`$ bats ./test/unit`

You'll need to install `bats` and `yq` first: 

```bash
brew install bats-core yq
```

## Purpose

These tests specify expected default behavior based on the templates and values used in this chart. We simulate use cases and test for outcomes.

These tests protect us from releasing breaking changes by verifying core functionality. Any time a new feature is added, we should create or modify these tests accordingly.
