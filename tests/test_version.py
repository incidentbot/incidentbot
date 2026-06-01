"""
Tests for incidentbot/version.py

The module resolves the app version in priority order:
  1. APP_VERSION env var  (set by the Docker build in CI)
  2. git describe         (local dev)
  3. "dev"               (fallback)
"""
import subprocess

import incidentbot.version as version_mod


def test_env_var_takes_priority(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "2024.05.31-abc1234")
    version_mod.get_app_version.cache_clear()

    assert version_mod.get_app_version() == "2024.05.31-abc1234"


def test_env_var_stripped_of_whitespace(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "  2024.05.31-abc1234  ")
    version_mod.get_app_version.cache_clear()

    assert version_mod.get_app_version() == "2024.05.31-abc1234"


def test_falls_back_to_git_describe(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    version_mod.get_app_version.cache_clear()

    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="v1.2.3-5-gabcdef0\n", stderr=""
    )
    monkeypatch.setattr(version_mod.subprocess, "run", lambda *a, **kw: fake_result)

    assert version_mod.get_app_version() == "v1.2.3-5-gabcdef0"


def test_falls_back_to_dev_when_git_fails(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    version_mod.get_app_version.cache_clear()

    fake_result = subprocess.CompletedProcess(
        args=[], returncode=128, stdout="", stderr="not a git repository"
    )
    monkeypatch.setattr(version_mod.subprocess, "run", lambda *a, **kw: fake_result)

    assert version_mod.get_app_version() == "dev"


def test_falls_back_to_dev_when_git_not_found(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)
    version_mod.get_app_version.cache_clear()

    def raise_file_not_found(*a, **kw):
        raise FileNotFoundError

    monkeypatch.setattr(version_mod.subprocess, "run", raise_file_not_found)

    assert version_mod.get_app_version() == "dev"


def test_empty_env_var_falls_through(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "")
    version_mod.get_app_version.cache_clear()

    fake_result = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="abcdef1\n", stderr=""
    )
    monkeypatch.setattr(version_mod.subprocess, "run", lambda *a, **kw: fake_result)

    # Empty string should be treated as unset — fall through to git
    assert version_mod.get_app_version() == "abcdef1"
