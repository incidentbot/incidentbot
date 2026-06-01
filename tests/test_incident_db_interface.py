"""
Tests for incidentbot/models/incident.py :: IncidentDatabaseInterface

All tests run against a SQLite in-memory engine via the ``db_engine`` fixture
from conftest.py. The real postgres engine is patched out in each test.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session

from incidentbot.models.database import (
    IncidentRecord,
    IncidentParticipant,
)
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.slack import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_engine(db_engine):
    """Patch the engine used by IncidentDatabaseInterface to the in-memory engine."""
    with (
        patch("incidentbot.models.incident.engine", db_engine),
        patch("incidentbot.incident.event.engine", db_engine),
    ):
        yield db_engine


@pytest.fixture()
def sample_incident(patched_engine):
    """Insert a single IncidentRecord and return it."""
    with Session(patched_engine) as session:
        record = IncidentRecord(
            id=1,
            channel_id="C_TEST",
            channel_name="incident-test",
            slug="inc-test",
            description="Test database outage",
            severity="sev2",
            status="investigating",
            is_security_incident=False,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


@pytest.fixture()
def sample_user():
    return User(id="U123", name="testuser", real_name="Test User", email="test@example.com")


# ---------------------------------------------------------------------------
# get_one
# ---------------------------------------------------------------------------

class TestGetOne:
    def test_get_by_channel_id(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.get_one(channel_id="C_TEST")
        assert result is not None
        assert result.channel_id == "C_TEST"

    def test_get_by_channel_name(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.get_one(channel_name="incident-test")
        assert result is not None
        assert result.channel_name == "incident-test"

    def test_get_by_id(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.get_one(id=1)
        assert result is not None
        assert result.id == 1

    def test_get_by_slug(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.get_one(slug="inc-test")
        assert result is not None
        assert result.slug == "inc-test"

    def test_returns_none_for_missing_incident(self, patched_engine):
        result = IncidentDatabaseInterface.get_one(channel_id="C_NONEXISTENT")
        assert result is None


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------

class TestListAll:
    def test_empty_db_returns_empty_list(self, patched_engine):
        result = IncidentDatabaseInterface.list_all()
        assert result == []

    def test_returns_all_incidents(self, patched_engine):
        with Session(patched_engine) as session:
            for i in range(3):
                session.add(IncidentRecord(
                    id=i + 10,
                    channel_id=f"C_{i}",
                    channel_name=f"incident-{i}",
                    slug=f"inc-{i}",
                    description=f"Outage {i}",
                    severity="sev3",
                    status="investigating",
                    is_security_incident=False,
                ))
            session.commit()

        result = IncidentDatabaseInterface.list_all()
        assert len(result) == 3


# ---------------------------------------------------------------------------
# list_open
# ---------------------------------------------------------------------------

class TestListOpen:
    def test_excludes_resolved_incidents(self, patched_engine):
        with Session(patched_engine) as session:
            session.add(IncidentRecord(
                id=20, channel_id="C_OPEN", channel_name="incident-open",
                slug="inc-open", description="Open", severity="sev1",
                status="investigating", is_security_incident=False,
            ))
            session.add(IncidentRecord(
                id=21, channel_id="C_RESOLVED", channel_name="incident-resolved",
                slug="inc-resolved", description="Closed", severity="sev4",
                status="resolved", is_security_incident=False,
            ))
            session.commit()

        mock_settings = MagicMock()
        mock_settings.statuses = {
            "investigating": SimpleNamespace(final=False),
            "resolved": SimpleNamespace(final=True),
        }
        with patch("incidentbot.models.incident.settings", mock_settings):
            result = IncidentDatabaseInterface.list_open()

        channel_ids = [r.channel_id for r in result]
        assert "C_OPEN" in channel_ids
        assert "C_RESOLVED" not in channel_ids

    def test_returns_all_when_no_final_status_configured(self, patched_engine):
        with Session(patched_engine) as session:
            session.add(IncidentRecord(
                id=30, channel_id="C_A", channel_name="incident-a",
                slug="inc-a", description="A", severity="sev1",
                status="investigating", is_security_incident=False,
            ))
            session.commit()

        mock_settings = MagicMock()
        mock_settings.statuses = {}  # no final statuses
        with patch("incidentbot.models.incident.settings", mock_settings):
            result = IncidentDatabaseInterface.list_open()

        assert len(result) >= 1


# ---------------------------------------------------------------------------
# list_recent
# ---------------------------------------------------------------------------

class TestListRecent:
    def test_returns_at_most_limit_incidents(self, patched_engine):
        with Session(patched_engine) as session:
            for i in range(8):
                session.add(IncidentRecord(
                    id=100 + i, channel_id=f"C_R{i}", channel_name=f"recent-{i}",
                    slug=f"inc-r{i}", description=f"Recent {i}", severity="sev3",
                    status="investigating", is_security_incident=False,
                ))
            session.commit()

        mock_settings = MagicMock()
        mock_settings.statuses = {"resolved": SimpleNamespace(final=True)}
        with patch("incidentbot.models.incident.settings", mock_settings):
            result = IncidentDatabaseInterface.list_recent(limit=3)

        assert len(result) <= 3

    def test_default_limit_is_5(self, patched_engine):
        with Session(patched_engine) as session:
            for i in range(10):
                session.add(IncidentRecord(
                    id=200 + i, channel_id=f"C_D{i}", channel_name=f"default-{i}",
                    slug=f"inc-d{i}", description=f"D {i}", severity="sev4",
                    status="investigating", is_security_incident=False,
                ))
            session.commit()

        mock_settings = MagicMock()
        mock_settings.statuses = {"resolved": SimpleNamespace(final=True)}
        with patch("incidentbot.models.incident.settings", mock_settings):
            result = IncidentDatabaseInterface.list_recent()

        assert len(result) <= 5


# ---------------------------------------------------------------------------
# update_col
# ---------------------------------------------------------------------------

class TestUpdateCol:
    @pytest.mark.parametrize("col,value", [
        ("channel_name", "incident-renamed"),
        ("description", "Updated description"),
        ("severity", "sev1"),
        ("status", "resolved"),
    ])
    def test_updates_column_by_channel_id(self, col, value, sample_incident, patched_engine):
        IncidentDatabaseInterface.update_col(
            col_name=col, value=value, channel_id="C_TEST"
        )
        with Session(patched_engine) as session:
            from sqlmodel import select
            updated = session.exec(
                select(IncidentRecord).filter(IncidentRecord.channel_id == "C_TEST")
            ).one()
        assert getattr(updated, col) == value

    def test_updates_column_by_id(self, sample_incident, patched_engine):
        IncidentDatabaseInterface.update_col(
            col_name="severity", value="sev4", id=1
        )
        with Session(patched_engine) as session:
            from sqlmodel import select
            updated = session.exec(
                select(IncidentRecord).filter(IncidentRecord.id == 1)
            ).one()
        assert updated.severity == "sev4"


# ---------------------------------------------------------------------------
# associate_role / check_role_assigned_to_user / list_participants / remove_role
# ---------------------------------------------------------------------------

class TestRoleManagement:
    def test_associate_role_creates_participant(self, sample_incident, sample_user, patched_engine):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident,
            is_lead=True,
            role="incident_commander",
            user=sample_user,
        )
        with Session(patched_engine) as session:
            from sqlmodel import select
            participants = session.exec(
                select(IncidentParticipant).filter(
                    IncidentParticipant.parent == sample_incident.id
                )
            ).all()
        assert len(participants) == 1
        assert participants[0].role == "incident_commander"
        assert participants[0].user_id == "U123"
        assert participants[0].is_lead is True

    def test_check_role_assigned_true(self, sample_incident, sample_user, patched_engine):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident, is_lead=False, role="comms_lead", user=sample_user
        )
        result = IncidentDatabaseInterface.check_role_assigned_to_user(
            incident=sample_incident, role="comms_lead", user=sample_user
        )
        assert result is True

    def test_check_role_assigned_false_for_different_role(
        self, sample_incident, sample_user, patched_engine
    ):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident, is_lead=False, role="comms_lead", user=sample_user
        )
        result = IncidentDatabaseInterface.check_role_assigned_to_user(
            incident=sample_incident, role="incident_commander", user=sample_user
        )
        assert result is False

    def test_check_role_assigned_false_for_different_user(
        self, sample_incident, sample_user, patched_engine
    ):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident, is_lead=False, role="comms_lead", user=sample_user
        )
        other_user = User(id="U999", name="other", real_name="Other User", email="o@example.com")
        result = IncidentDatabaseInterface.check_role_assigned_to_user(
            incident=sample_incident, role="comms_lead", user=other_user
        )
        assert result is False

    def test_list_participants(self, sample_incident, sample_user, patched_engine):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident, is_lead=True, role="incident_commander", user=sample_user
        )
        result = IncidentDatabaseInterface.list_participants(incident=sample_incident)
        assert len(result) == 1
        assert result[0].role == "incident_commander"

    def test_list_participants_empty(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.list_participants(incident=sample_incident)
        assert result == []

    def test_remove_role(self, sample_incident, sample_user, patched_engine):
        IncidentDatabaseInterface.associate_role(
            incident=sample_incident, is_lead=False, role="comms_lead", user=sample_user
        )
        IncidentDatabaseInterface.remove_role(
            incident=sample_incident, role="comms_lead", user=sample_user
        )
        result = IncidentDatabaseInterface.list_participants(incident=sample_incident)
        assert len(result) == 0


# ---------------------------------------------------------------------------
# add_postmortem / get_postmortem
# ---------------------------------------------------------------------------

class TestPostmortemRecords:
    def test_add_and_get_postmortem(self, sample_incident, patched_engine):
        url = "https://example.atlassian.net/wiki/spaces/OPS/pages/12345"
        IncidentDatabaseInterface.add_postmortem(parent=sample_incident.id, url=url)
        result = IncidentDatabaseInterface.get_postmortem(parent=sample_incident.id)
        assert result is not None
        assert result.url == url
        assert result.parent == sample_incident.id

    def test_get_postmortem_returns_none_when_absent(self, sample_incident, patched_engine):
        result = IncidentDatabaseInterface.get_postmortem(parent=sample_incident.id)
        assert result is None
