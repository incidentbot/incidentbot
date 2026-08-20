from pathlib import Path

import pytest
from pydantic import ValidationError

from incidentbot.configuration.settings import Settings


def _set_minimal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_DB", "incident_bot")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "incident_bot")
    monkeypatch.setenv("PLATFORM", "matrix")

    # Clear any MATRIX_* vars from the developer's own shell, otherwise a real
    # local token leaks in and overrides what the test sets up.
    for var in (
        "MATRIX_HOMESERVER",
        "MATRIX_USER_ID",
        "MATRIX_ACCESS_TOKEN",
        "MATRIX_DEVICE_ID",
        "MATRIX_DIGEST_ROOM_ID",
        "MATRIX_WIDGET_BASE_URL",
    ):
        monkeypatch.delenv(var, raising=False)


def _set_yaml_file(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setitem(Settings.model_config, "yaml_file", str(path))


def test_matrix_settings_can_be_loaded_from_env(monkeypatch, tmp_path):
    _set_minimal_env(monkeypatch)
    _set_yaml_file(monkeypatch, tmp_path / "config.yaml")

    monkeypatch.setenv("MATRIX_HOMESERVER", "https://matrix.example.com")
    monkeypatch.setenv("MATRIX_USER_ID", "@incidentbot:example.com")
    monkeypatch.setenv("MATRIX_ACCESS_TOKEN", "syt_env_token")
    monkeypatch.setenv("MATRIX_DEVICE_ID", "ENVDEVICE")
    monkeypatch.setenv("MATRIX_DIGEST_ROOM_ID", "!digest:example.com")
    monkeypatch.setenv("MATRIX_WIDGET_BASE_URL", "https://incidentbot.example.com")

    settings = Settings()

    assert settings.matrix is not None
    assert settings.matrix.homeserver == "https://matrix.example.com"
    assert settings.matrix.user_id == "@incidentbot:example.com"
    assert settings.matrix.access_token == "syt_env_token"
    assert settings.matrix.device_id == "ENVDEVICE"
    assert settings.matrix.digest_room_id == "!digest:example.com"
    assert settings.matrix.widget_base_url == "https://incidentbot.example.com"


def test_matrix_env_vars_override_yaml_matrix_config(monkeypatch, tmp_path):
    _set_minimal_env(monkeypatch)

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
platform: matrix
matrix:
  homeserver: https://yaml.example.com
  user_id: "@yaml-bot:example.com"
  access_token: yaml_token
  device_id: YAMLDEVICE
  digest_room_id: "!yaml:example.com"
  widget_base_url: https://yaml-widget.example.com
""".strip()
        + "\n"
    )
    _set_yaml_file(monkeypatch, config_file)

    monkeypatch.setenv("MATRIX_HOMESERVER", "https://env.example.com")
    monkeypatch.setenv("MATRIX_DEVICE_ID", "ENVDEVICE")

    settings = Settings()

    assert settings.matrix is not None
    assert settings.matrix.homeserver == "https://env.example.com"
    assert settings.matrix.user_id == "@yaml-bot:example.com"
    assert settings.matrix.access_token == "yaml_token"
    assert settings.matrix.device_id == "ENVDEVICE"
    assert settings.matrix.digest_room_id == "!yaml:example.com"
    assert settings.matrix.widget_base_url == "https://yaml-widget.example.com"


def test_platform_can_be_loaded_from_env_and_override_yaml(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_DB", "incident_bot")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "incident_bot")
    monkeypatch.setenv("PLATFORM", "matrix")
    monkeypatch.setenv("MATRIX_HOMESERVER", "https://env.example.com")
    monkeypatch.setenv("MATRIX_USER_ID", "@incidentbot:example.com")
    monkeypatch.setenv("MATRIX_ACCESS_TOKEN", "env_token")
    monkeypatch.setenv("MATRIX_DIGEST_ROOM_ID", "!digest:example.com")

    config_file = tmp_path / "config.yaml"
    config_file.write_text("platform: slack\n")
    _set_yaml_file(monkeypatch, config_file)

    settings = Settings()

    assert settings.platform == "matrix"
    assert settings.matrix is not None
    assert settings.matrix.homeserver == "https://env.example.com"


def test_invalid_platform_value_fails_fast(monkeypatch, tmp_path):
    monkeypatch.setenv("POSTGRES_DB", "incident_bot")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PASSWORD", "password")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "incident_bot")
    monkeypatch.setenv("PLATFORM", "materix")
    _set_yaml_file(monkeypatch, tmp_path / "config.yaml")

    with pytest.raises(ValidationError):
        Settings()
