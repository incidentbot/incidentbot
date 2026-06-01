#!/usr/bin/env python3
"""Sync Python version references across repo config files."""

from __future__ import annotations

import re
import sys
from pathlib import Path


def _replace_once(path: Path, pattern: str, replacement: str) -> None:
    content = path.read_text(encoding="utf-8")
    updated, count = re.subn(pattern, replacement, content, count=1)
    if count != 1:
        raise RuntimeError(f"expected exactly one match in {path}: {pattern}")
    path.write_text(updated, encoding="utf-8")
    print(f"updated {path}")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: sync_python_version.py <python_version>")
        return 2

    python_version = sys.argv[1]
    parts = python_version.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid python version: {python_version}")
    major, minor, _patch = parts
    ruff_target = f"py{major}{minor}"

    root = Path(__file__).resolve().parents[1]
    updates: list[tuple[str, str, str]] = [
        (
            "pyproject.toml",
            r'(?m)^python = "\^\d+\.\d+\.\d+"$',
            f'python = "^{python_version}"',
        ),
        (
            "Dockerfile",
            r"(?m)^ARG PYTHON_VERSION=\d+\.\d+\.\d+$",
            f"ARG PYTHON_VERSION={python_version}",
        ),
        (
            "ruff.toml",
            r'(?m)^target-version = "py\d+"$',
            f'target-version = "{ruff_target}"',
        ),
    ]

    for rel, pattern, replacement in updates:
        _replace_once(root / rel, pattern, replacement)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
