"""
Tests for GET /api/v1/incidents and GET /api/v1/metrics.
"""
import unittest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch

# ── Patch boot-time deps before any incidentbot import ────────────────────────
_mock_settings = MagicMock()
_mock_settings.API_KEY = None
_mock_settings.IS_TEST_ENVIRONMENT = True
_mock_settings.DATABASE_URI = "sqlite:///:memory:"
_mock_settings.SLACK_BOT_TOKEN = "test-token"
_mock_settings.LOG_LEVEL = "INFO"
_mock_settings.LOG_TYPE = None
_mock_settings.statuses = {
    "investigating": MagicMock(final=False),
    "resolved": MagicMock(final=True),
}

with (
    patch("incidentbot.configuration.settings.settings", _mock_settings),
    patch("sqlmodel.create_engine", return_value=MagicMock()),
    patch("slack_sdk.WebClient", return_value=MagicMock()),
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from incidentbot.api.routes.incidents import router

_app = FastAPI()
_app.include_router(router)
client = TestClient(_app)


# ── Factories ─────────────────────────────────────────────────────────────────


def _make_incident(
    id=1,
    slug="inc-test",
    status="investigating",
    severity="sev2",
):
    inc = MagicMock()
    inc.id = id
    inc.slug = slug
    inc.description = "Test incident"
    inc.severity = severity
    inc.status = status
    inc.components = "api"
    inc.impact = "high"
    inc.is_security_incident = False
    inc.channel_id = f"C{id:04d}"
    inc.channel_name = slug
    inc.link = None
    inc.meeting_link = None
    inc.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    inc.updated_at = datetime(2025, 1, 1, 2, tzinfo=UTC)
    return inc


def _make_session(incidents=None, participants=None, count=None):
    """Return a mock Session context manager for list/get routes."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    incidents = incidents or []
    participants = participants or []

    # execute(...).scalar_one() → total count
    session.execute.return_value.scalar_one.return_value = (
        count if count is not None else len(incidents)
    )

    # exec(...).all() is called once for the incident list, then once per
    # incident for participants — wire up side_effect for sequential calls.
    exec_all_values = [incidents] + [participants] * max(len(incidents), 1)
    exec_mock = MagicMock()
    exec_mock.all.side_effect = exec_all_values
    session.exec.return_value = exec_mock

    return session


def _make_metrics_session(
    total=0,
    open_count=0,
    severity_rows=None,
    status_rows=None,
    avg_seconds=None,
    last_7=0,
    last_30=0,
):
    """Return a mock Session context manager for the metrics route."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    # Build per-call results for session.execute in the order the route calls them:
    #   1. total count         → scalar_one
    #   2. open count          → scalar_one
    #   3. by_severity GROUP BY → all
    #   4. by_status  GROUP BY  → all
    #   5. avg MTTR             → scalar
    #   6. last_7_days count    → scalar_one
    #   7. last_30_days count   → scalar_one
    def _r(scalar_one=None, scalar=None, all_val=None):
        m = MagicMock()
        m.scalar_one.return_value = scalar_one
        m.scalar.return_value = scalar
        m.all.return_value = all_val or []
        return m

    session.execute.side_effect = [
        _r(scalar_one=total),
        _r(scalar_one=open_count),
        _r(all_val=severity_rows or []),
        _r(all_val=status_rows or []),
        _r(scalar=avg_seconds),
        _r(scalar_one=last_7),
        _r(scalar_one=last_30),
    ]
    return session


# ── List incidents ────────────────────────────────────────────────────────────


class TestListIncidents(unittest.TestCase):
    def test_empty_returns_200(self):
        session = _make_session()
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["incidents"], [])
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["offset"], 0)

    def test_returns_incidents(self):
        inc = _make_incident()
        session = _make_session(incidents=[inc])
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 1)
        self.assertEqual(len(body["incidents"]), 1)
        self.assertEqual(body["incidents"][0]["slug"], "inc-test")
        self.assertEqual(body["incidents"][0]["severity"], "sev2")
        self.assertEqual(body["incidents"][0]["status"], "investigating")

    def test_incident_includes_participants(self):
        inc = _make_incident()
        participant = MagicMock()
        participant.role = "incident_commander"
        participant.user_id = "U001"
        participant.user_name = "alice"
        participant.is_lead = True
        session = _make_session(incidents=[inc], participants=[participant])
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents")
        participants = resp.json()["incidents"][0]["participants"]
        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0]["role"], "incident_commander")
        self.assertTrue(participants[0]["is_lead"])

    def test_pagination_params_forwarded(self):
        session = _make_session(count=100)
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents?limit=10&offset=20")
        body = resp.json()
        self.assertEqual(body["limit"], 10)
        self.assertEqual(body["offset"], 20)

    def test_limit_must_be_positive(self):
        resp = client.get("/api/v1/incidents?limit=0")
        self.assertEqual(resp.status_code, 422)

    def test_offset_must_be_non_negative(self):
        resp = client.get("/api/v1/incidents?offset=-1")
        self.assertEqual(resp.status_code, 422)


# ── Get single incident ───────────────────────────────────────────────────────


class TestGetIncident(unittest.TestCase):
    def test_returns_incident(self):
        inc = _make_incident(id=42)
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.get.return_value = inc
        session.exec.return_value.all.return_value = []

        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents/42")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["id"], 42)

    def test_returns_404_when_missing(self):
        session = MagicMock()
        session.__enter__ = MagicMock(return_value=session)
        session.__exit__ = MagicMock(return_value=False)
        session.get.return_value = None

        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/incidents/999")

        self.assertEqual(resp.status_code, 404)


# ── Metrics ───────────────────────────────────────────────────────────────────


class TestMetrics(unittest.TestCase):
    def test_returns_200_with_correct_shape(self):
        session = _make_metrics_session(
            total=10,
            open_count=3,
            severity_rows=[("sev1", 2), ("sev2", 8)],
            status_rows=[("investigating", 3), ("resolved", 7)],
            avg_seconds=7200.0,
            last_7=2,
            last_30=5,
        )
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/metrics")

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["total"], 10)
        self.assertEqual(body["open"], 3)
        self.assertEqual(body["by_severity"], {"sev1": 2, "sev2": 8})
        self.assertEqual(body["by_status"], {"investigating": 3, "resolved": 7})
        self.assertAlmostEqual(body["mttr_hours"], 2.0)
        self.assertEqual(body["last_7_days"], 2)
        self.assertEqual(body["last_30_days"], 5)

    def test_mttr_is_none_when_no_resolved_incidents(self):
        session = _make_metrics_session(avg_seconds=None)
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/metrics")
        self.assertIsNone(resp.json()["mttr_hours"])

    def test_empty_database_returns_zeros(self):
        session = _make_metrics_session()
        with patch("incidentbot.api.routes.incidents.Session", return_value=session):
            resp = client.get("/api/v1/metrics")
        body = resp.json()
        self.assertEqual(body["total"], 0)
        self.assertEqual(body["open"], 0)
        self.assertEqual(body["by_severity"], {})
        self.assertEqual(body["by_status"], {})
        self.assertIsNone(body["mttr_hours"])


# ── API key auth ──────────────────────────────────────────────────────────────


class TestApiKeyAuth(unittest.TestCase):
    def _patched_settings(self, key):
        m = MagicMock()
        m.configure_mock(**{k: getattr(_mock_settings, k) for k in dir(_mock_settings)})
        m.API_KEY = key
        m.statuses = _mock_settings.statuses
        return m

    def test_no_key_set_allows_all_requests(self):
        session = _make_session()
        with (
            patch("incidentbot.api.routes.incidents.Session", return_value=session),
            patch("incidentbot.api.routes.incidents.settings", _mock_settings),
        ):
            resp = client.get("/api/v1/incidents")
        self.assertEqual(resp.status_code, 200)

    def test_correct_key_allows_request(self):
        patched = self._patched_settings("secret-key")
        session = _make_session()
        with (
            patch("incidentbot.api.routes.incidents.Session", return_value=session),
            patch("incidentbot.api.routes.incidents.settings", patched),
        ):
            resp = client.get(
                "/api/v1/incidents", headers={"X-Api-Key": "secret-key"}
            )
        self.assertEqual(resp.status_code, 200)

    def test_wrong_key_returns_403(self):
        patched = self._patched_settings("secret-key")
        with patch("incidentbot.api.routes.incidents.settings", patched):
            resp = client.get(
                "/api/v1/incidents", headers={"X-Api-Key": "wrong-key"}
            )
        self.assertEqual(resp.status_code, 403)

    def test_missing_key_returns_403(self):
        patched = self._patched_settings("secret-key")
        with patch("incidentbot.api.routes.incidents.settings", patched):
            resp = client.get("/api/v1/incidents")
        self.assertEqual(resp.status_code, 403)
