"""
App version — derived automatically, never set by hand.

Resolution order:
  1. APP_VERSION env var  — baked in by the Docker build (format: YYYY.MM.DD-<sha>)
  2. `git describe`       — useful during local development
  3. "dev"                — fallback when neither is available
"""
import os
import subprocess
from functools import lru_cache


@lru_cache(maxsize=1)
def get_app_version() -> str:
    env_version = os.environ.get("APP_VERSION", "").strip()
    if env_version:
        return env_version

    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return "dev"


APP_VERSION = get_app_version()
