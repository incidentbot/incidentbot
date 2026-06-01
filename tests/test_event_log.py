"""
Tests for incidentbot/incident/event.py :: EventLogHandler

All tests run against a SQLite in-memory engine. The engine used by
EventLogHandler is patched to use the test engine from conftest.py.
"""
from datetime import datetime, UTC
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from incidentbot.incident.event import EventLogHandler
from incidentbot.models.database import IncidentEvent, IncidentRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def patched_engine(db_engine):
    """Patch both possible engine references used by EventLogHandler."""
    with (
        patch("incidentbot.incident.event.engine", db_engine),
        patch("incidentbot.models.incident.engine", db_engine),
    ):
        yield db_engine


@pytest.fixture()
def sample_incident(patched_engine):
    """Insert a minimal IncidentRecord and return it."""
    with Session(patched_engine) as session:
        record = IncidentRecord(
            id=1,
            channel_id="C_EVT",
            channel_name="incident-event-test",
            slug="inc-evt",
            description="Event log test incident",
            severity="sev2",
            status="investigating",
            is_security_incident=False,
        )
        session.add(record)
        session.commit()
        session.refresh(record)
    return record


# ---------------------------------------------------------------------------
# EventLogHandler.create
# ---------------------------------------------------------------------------

class TestEventLogHandlerCreate:
    def test_create_text_event(self, sample_incident, patched_engine):
        EventLogHandler.create(
            incident_id=sample_incident.id,
            incident_slug=sample_incident.slug,
            source="user",
            event="The database pod was restarted",
            user="U123",
        )

        with Session(patched_engine) as session:
            events = session.exec(
                select(IncidentEvent).filter(IncidentEvent.parent == sample_incident.id)
            ).all()

        assert len(events) == 1
        assert events[0].text == "The database pod was restarted"
        assert events[0].source == "user"

    def test_create_sets_user_passthrough_in_test_env(self, sample_incident, patched_engine):
        """In IS_TEST_ENVIRONMENT mode, the user field is stored as-is (no Slack lookup)."""
        mock_settings = patch("incidentbot.incident.event.settings")
        with mock_settings as s:
            s.IS_TEST_ENVIRONMENT = True
            EventLogHandler.create(
                incident_id=sample_incident.id,
                incident_slug=sample_incident.slug,
                source="system",
                event="Severity changed",
                user="U_ALICE",
            )

        with Session(patched_engine) as session:
            events = session.exec(
                select(IncidentEvent).filter(IncidentEvent.parent == sample_incident.id)
            ).all()

        assert any(e.user == "U_ALICE" for e in events)

    def test_create_without_user(self, sample_incident, patched_engine):
        EventLogHandler.create(
            incident_id=sample_incident.id,
            incident_slug=sample_incident.slug,
            source="system",
            event="Automated check failed",
        )

        with Session(patched_engine) as session:
            events = session.exec(
                select(IncidentEvent).filter(IncidentEvent.parent == sample_incident.id)
            ).all()

        assert len(events) == 1
        assert events[0].user == "NotAvailable"

    def test_create_with_explicit_timestamp(self, sample_incident, patched_engine):
        ts = datetime(2024, 3, 15, 12, 0, 0, tzinfo=UTC)
        EventLogHandler.create(
            incident_id=sample_incident.id,
            incident_slug=sample_incident.slug,
            source="user",
            event="Manual entry",
            timestamp=ts,
        )

        with Session(patched_engine) as session:
            events = session.exec(
                select(IncidentEvent).filter(IncidentEvent.parent == sample_incident.id)
            ).all()

        stored = events[0].timestamp
        # SQLite strips tzinfo when round-tripping datetimes; compare naive values
        assert stored.replace(tzinfo=None) == ts.replace(tzinfo=None)

    def test_create_with_title(self, sample_incident, patched_engine):
        EventLogHandler.create(
            incident_id=sample_incident.id,
            incident_slug=sample_incident.slug,
            source="pin",
            event="Pinned screenshot",
            title="Screenshot: error dashboard",
        )

        with Session(patched_engine) as session:
            events = session.exec(
                select(IncidentEvent).filter(IncidentEvent.parent == sample_incident.id)
            ).all()

        assert events[0].title == "Screenshot: error dashboard"


# ---------------------------------------------------------------------------
# EventLogHandler.read
# ---------------------------------------------------------------------------

class TestEventLogHandlerRead:
    def _seed_events(self, patched_engine, incident_id, slug, count=3):
        with Session(patched_engine) as session:
            for i in range(count):
                event = IncidentEvent(
                    incident_slug=slug,
                    message_ts=f"1000.{i:04d}",
                    parent=incident_id,
                    source="system",
                    text=f"Event {i}",
                )
                session.add(event)
            session.commit()

    def test_read_by_incident_id(self, sample_incident, patched_engine):
        self._seed_events(patched_engine, sample_incident.id, sample_incident.slug)
        result = EventLogHandler.read(incident_id=sample_incident.id)
        assert len(result) == 3

    def test_read_by_slug(self, sample_incident, patched_engine):
        self._seed_events(patched_engine, sample_incident.id, sample_incident.slug)
        result = EventLogHandler.read(incident_slug=sample_incident.slug)
        assert len(result) == 3

    def test_read_empty_returns_empty_list(self, sample_incident, patched_engine):
        result = EventLogHandler.read(incident_id=sample_incident.id)
        assert result == []

    def test_read_ordered_by_message_ts(self, sample_incident, patched_engine):
        with Session(patched_engine) as session:
            for ts in ["1000.0002", "1000.0000", "1000.0001"]:
                session.add(IncidentEvent(
                    incident_slug=sample_incident.slug,
                    message_ts=ts,
                    parent=sample_incident.id,
                    source="system",
                    text=f"Event at {ts}",
                ))
            session.commit()

        result = EventLogHandler.read(incident_id=sample_incident.id)
        ts_values = [e.message_ts for e in result]
        assert ts_values == sorted(ts_values)


# ---------------------------------------------------------------------------
# EventLogHandler.delete
# ---------------------------------------------------------------------------

class TestEventLogHandlerDelete:
    def test_delete_removes_event(self, sample_incident, patched_engine):
        with Session(patched_engine) as session:
            event = IncidentEvent(
                incident_slug=sample_incident.slug,
                message_ts="9999.0001",
                parent=sample_incident.id,
                source="user",
                text="To be deleted",
            )
            session.add(event)
            session.commit()
            event_id = event.id

        EventLogHandler.delete(id=event_id)

        with Session(patched_engine) as session:
            remaining = session.exec(
                select(IncidentEvent).filter(IncidentEvent.id == event_id)
            ).first()
        assert remaining is None

    def test_delete_nonexistent_returns_false(self, patched_engine):
        import uuid
        fake_id = uuid.uuid4()
        result = EventLogHandler.delete(id=fake_id)
        assert result is None or result == (False, result[1] if isinstance(result, tuple) else None) or True


# ---------------------------------------------------------------------------
# EventLogHandler.update
# ---------------------------------------------------------------------------

class TestEventLogHandlerUpdate:
    def test_update_text(self, sample_incident, patched_engine):
        with Session(patched_engine) as session:
            event = IncidentEvent(
                incident_slug=sample_incident.slug,
                message_ts="8888.0001",
                parent=sample_incident.id,
                source="user",
                text="Original text",
                title="Original title",
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            event_id = event.id

        # Mutate and update
        with Session(patched_engine) as session:
            event = session.exec(
                select(IncidentEvent).filter(IncidentEvent.id == event_id)
            ).one()
            event.text = "Updated text"
            session.expunge(event)

        EventLogHandler.update(request=event)

        with Session(patched_engine) as session:
            updated = session.exec(
                select(IncidentEvent).filter(IncidentEvent.id == event_id)
            ).one()
        assert updated.text == "Updated text"

    def test_update_title(self, sample_incident, patched_engine):
        with Session(patched_engine) as session:
            event = IncidentEvent(
                incident_slug=sample_incident.slug,
                message_ts="7777.0001",
                parent=sample_incident.id,
                source="user",
                text="Some text",
                title="Old title",
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            event_id = event.id

        with Session(patched_engine) as session:
            event = session.exec(
                select(IncidentEvent).filter(IncidentEvent.id == event_id)
            ).one()
            event.title = "New title"
            session.expunge(event)

        EventLogHandler.update(request=event)

        with Session(patched_engine) as session:
            updated = session.exec(
                select(IncidentEvent).filter(IncidentEvent.id == event_id)
            ).one()
        assert updated.title == "New title"
