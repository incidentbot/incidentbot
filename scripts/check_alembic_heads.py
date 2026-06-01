#!/usr/bin/env python3
"""Validate Alembic revision graph has exactly one head."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


def _parse_symbol(content: str, symbol: str):
    match = re.search(rf"(?m)^{symbol}\s*=\s*(.+?)\s*$", content)
    if not match:
        raise ValueError(f"could not find {symbol} assignment")
    return ast.literal_eval(match.group(1))


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    versions_dir = repo_root / "alembic" / "versions"
    revision_files = sorted(versions_dir.glob("*.py"))
    if not revision_files:
        raise ValueError(f"no revision files found in {versions_dir}")

    revisions: set[str] = set()
    referenced: set[str] = set()

    for file in revision_files:
        content = file.read_text(encoding="utf-8")
        revision = _parse_symbol(content, "revision")
        down_revision = _parse_symbol(content, "down_revision")

        if not isinstance(revision, str) or not revision:
            raise ValueError(f"invalid revision in {file}")
        revisions.add(revision)

        if down_revision is None:
            continue
        if isinstance(down_revision, str):
            referenced.add(down_revision)
            continue
        if isinstance(down_revision, (tuple, list)):
            for parent in down_revision:
                if isinstance(parent, str) and parent:
                    referenced.add(parent)
            continue
        raise ValueError(f"invalid down_revision in {file}: {down_revision}")

    heads = sorted(revisions - referenced)
    print("alembic heads:", ", ".join(heads))
    if len(heads) != 1:
        print(
            f"expected exactly 1 alembic head, found {len(heads)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
