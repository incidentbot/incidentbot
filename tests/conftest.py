"""
Shared pytest fixtures for incidentbot tests.

``db_engine`` — a fresh SQLite in-memory engine with all tables created.
Modules that import ``engine`` from ``incidentbot.models.database`` are
patched to use this engine inside any test that requests ``patch_db_engine``.
"""
import sys
from unittest.mock import MagicMock

# Permanently mock the scheduler before any incidentbot module that imports it
# is collected.  Without this, test files that import action/reminder modules
# would pull in the real APScheduler and attempt to start background threads.
if "incidentbot.scheduler.core" not in sys.modules:
    sys.modules["incidentbot.scheduler.core"] = MagicMock()

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, SQLModel

# Register all table metadata by importing the models package.
import incidentbot.models.database  # noqa: F401


def make_test_engine():
    """Return a fresh SQLite in-memory engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture()
def db_engine():
    """
    Fresh SQLite in-memory engine per test function.

    Each test gets a clean slate — tables are created before the test runs and
    dropped afterwards (the in-memory DB is discarded when the engine goes out
    of scope).
    """
    engine = make_test_engine()
    yield engine
