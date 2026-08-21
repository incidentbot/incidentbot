import re
from pathlib import Path

import yaml

from incidentbot.configuration.settings import Options, Settings

REPO_ROOT = Path(__file__).resolve().parents[1]


def _env_keys_from_sample() -> set[str]:
    keys: set[str] = set()

    for line in (REPO_ROOT / ".env.sample").read_text().splitlines():
        stripped = line.strip()
        # Commented-out assignments like "# API_KEY=" still document a key.
        if stripped.startswith("#"):
            stripped = stripped.lstrip("#").strip()
        if not stripped or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key and re.fullmatch(r"[A-Z][A-Z0-9_]*", key):
            keys.add(key)

    return keys


def _env_keys_from_compose(path: Path) -> set[str]:
    loaded = yaml.safe_load(path.read_text()) or {}
    services = loaded.get("services", {})
    keys: set[str] = set()

    for service in services.values():
        environment = service.get("environment")
        if isinstance(environment, dict):
            keys.update(k for k in environment if isinstance(k, str))
        elif isinstance(environment, list):
            for item in environment:
                if isinstance(item, str) and "=" in item:
                    key = item.split("=", 1)[0].strip()
                    if key:
                        keys.add(key)

    return keys


def test_env_sample_matches_settings_env_fields():
    settings_env_keys = {name for name in Settings.model_fields if name.isupper()}
    sample_keys = _env_keys_from_sample()
    # PLATFORM maps to the lowercase `platform` field (env parsing is
    # case-insensitive); COMPOSE_* keys are docker-compose substitution
    # variables, not app settings.
    allowed_extras = {"CONFIG_FILE_PATH", "PLATFORM"}
    # Internal runtime flags, not user-facing configuration.
    internal_settings = {"IS_MIGRATION", "IS_TEST_ENVIRONMENT"}

    missing = sorted(settings_env_keys - sample_keys - internal_settings)
    unknown = sorted(
        key
        for key in sample_keys - settings_env_keys - allowed_extras
        if not key.startswith("COMPOSE_")
    )

    assert not missing, f".env.sample is missing settings keys: {missing}"
    assert not unknown, f".env.sample contains unknown keys: {unknown}"


def test_compose_environment_keys_are_known():
    settings_env_keys = {name for name in Settings.model_fields if name.isupper()}
    allowed_extras = {"CONFIG_FILE_PATH"}

    compose_files = sorted(REPO_ROOT.glob("docker-compose*.yml"))
    assert compose_files, "No docker-compose*.yml files found"

    for compose_path in compose_files:
        compose_keys = _env_keys_from_compose(compose_path)
        unknown = sorted(
            key
            for key in compose_keys
            if key.isupper()
            and key not in settings_env_keys
            and key not in allowed_extras
        )
        assert not unknown, f"{compose_path.name} contains unknown env keys: {unknown}"


def test_options_model_matches_option_references():
    source = "\n".join(
        path.read_text() for path in (REPO_ROOT / "incidentbot").rglob("*.py")
    )
    referenced = set(re.findall(r"settings\.options\.([a-zA-Z0-9_]+)", source))
    defined = set(Options.model_fields)
    missing = sorted(referenced - defined)

    assert not missing, f"Undefined settings.options references found: {missing}"
