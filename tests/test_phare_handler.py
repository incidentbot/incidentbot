import importlib
import unittest
from unittest.mock import patch, MagicMock, call

# ---------------------------------------------------------------------------
# Patch boot-time dependencies before any incidentbot import
# ---------------------------------------------------------------------------
mock_settings = MagicMock()
mock_settings.PHARE_API_KEY = "test-api-key"
mock_settings.PHARE_PROJECT_ID = "proj-123"
mock_settings.DATABASE_URI = "sqlite:///:memory:"
mock_settings.SLACK_BOT_TOKEN = "test-token"
mock_settings.LOG_LEVEL = "INFO"
mock_settings.LOG_TYPE = None
mock_settings.IS_TEST_ENVIRONMENT = True

with (
    patch("incidentbot.configuration.settings.settings", mock_settings),
    patch("sqlmodel.create_engine", return_value=MagicMock()),
    patch("slack_sdk.WebClient", return_value=MagicMock()),
    patch("apscheduler.schedulers.background.BackgroundScheduler"),
):
    import incidentbot.phare.handler as _phare_handler_mod
    # Force a reload so phare.handler.settings binds to our mock_settings,
    # even if another test file already imported it with a different mock.
    importlib.reload(_phare_handler_mod)
    from incidentbot.phare.handler import PhareMonitors, PhareIncident, PhareIncidentUpdate
    from incidentbot.slack.util import parse_modal_values


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(json_data, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = json_data
    r.raise_for_status = MagicMock()
    return r


def _make_record(upstream_id=99, state="investigating", updates=None, url=None):
    r = MagicMock()
    r.upstream_id = upstream_id
    r.state = state
    r.updates = updates if updates is not None else []
    r.message_ts = "111.222"
    r.url = url
    return r


def _setup_session(mock_session, record):
    ctx = MagicMock()
    ctx.exec.return_value.one.return_value = record
    mock_session.return_value.__enter__.return_value = ctx
    return ctx


def _setup_incident(mock_get_one, channel_id="C123", incident_id=7, channel_name="incident-1"):
    inc = MagicMock()
    inc.id = incident_id
    inc.channel_id = channel_id
    inc.channel_name = channel_name
    mock_get_one.return_value = inc
    return inc


# ---------------------------------------------------------------------------
# PhareMonitors
# ---------------------------------------------------------------------------

class TestPhareMonitors(unittest.TestCase):
    @patch("incidentbot.phare.handler.requests.get")
    def test_single_page(self, mock_get):
        mock_get.return_value = _resp({
            "data": [{"id": 1, "name": "API"}, {"id": 2, "name": "Web"}],
            "links": {"next": None},
        })

        pm = PhareMonitors()

        mock_get.assert_called_once_with(
            "https://api.phare.io/uptime/monitors",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
            params={"page": 1, "per_page": 100},
        )
        self.assertEqual(pm.list_of_names, ["API", "Web"])
        self.assertEqual(pm.list_of_dict_name_ids, [{"API": 1}, {"Web": 2}])

    @patch("incidentbot.phare.handler.requests.get")
    def test_pagination_fetches_all_pages(self, mock_get):
        mock_get.side_effect = [
            _resp({
                "data": [{"id": 1, "name": "API"}],
                "links": {"next": "https://api.phare.io/uptime/monitors?page=2"},
            }),
            _resp({
                "data": [{"id": 2, "name": "Web"}],
                "links": {"next": None},
            }),
        ]

        pm = PhareMonitors()

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(pm.list_of_names, ["API", "Web"])

    @patch("incidentbot.phare.handler.requests.get")
    def test_http_error_raises(self, mock_get):
        import requests as _requests
        mock_get.return_value.raise_for_status.side_effect = _requests.exceptions.HTTPError("401")
        mock_get.return_value.json.return_value = {}
        with self.assertRaises(_requests.exceptions.HTTPError):
            PhareMonitors()


# ---------------------------------------------------------------------------
# PhareIncident
# ---------------------------------------------------------------------------

class TestPhareIncident(unittest.TestCase):
    def _make(self, overrides=None):
        data = {
            "title": "DB outage",
            "description": "Primary DB is down",
            "impact": "major_outage",
            "monitors": [42],
            "exclude_from_downtime": False,
            "channel_id": "C123",
        }
        if overrides:
            data.update(overrides)
        return PhareIncident(data)

    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.slack_web_client")
    @patch("incidentbot.phare.handler.requests.post")
    def test_start_creates_incident_posts_initial_update_and_stores_record(
        self, mock_post, mock_slack, mock_get_one, mock_session
    ):
        create_resp = _resp({"id": 99, "title": "DB outage", "state": "unknown", "url": None})
        update_resp = _resp({"state": "investigating"})
        mock_post.side_effect = [create_resp, update_resp]

        mock_slack.conversations_history.return_value = {
            "messages": [
                {"text": "Phare prompt has been posted to an incident.", "ts": "111.222"},
            ]
        }
        _setup_incident(mock_get_one)
        ctx = _setup_session(mock_session, MagicMock())

        incident = self._make()
        ts = incident.start()

        # First POST creates the incident
        self.assertEqual(mock_post.call_args_list[0], call(
            "https://api.phare.io/uptime/incidents",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
            json={
                "title": "DB outage",
                "description": "Primary DB is down",
                "impact": "major_outage",
                "monitors": [42],
                "exclude_from_downtime": False,
            },
        ))
        # Second POST publishes initial investigating state
        self.assertEqual(mock_post.call_args_list[1], call(
            "https://api.phare.io/uptime/incidents/99/updates",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
            json={"state": "investigating", "content": "Incident is being investigated."},
        ))
        self.assertEqual(ts, "111.222")
        ctx.add.assert_called_once()
        ctx.commit.assert_called_once()

    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.slack_web_client")
    @patch("incidentbot.phare.handler.requests.post")
    def test_start_returns_none_on_api_error(self, mock_post, mock_slack, mock_get_one, mock_session):
        mock_post.return_value.raise_for_status.side_effect = Exception("500")
        mock_slack.conversations_history.return_value = {"messages": []}

        result = self._make().start()

        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# PhareIncidentUpdate.update
# ---------------------------------------------------------------------------

class TestPhareIncidentUpdateUpdate(unittest.TestCase):
    @patch("incidentbot.phare.handler.slack_web_client")
    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.requests.post")
    def test_state_update_posts_to_updates_endpoint(self, mock_post, mock_get_one, mock_session, mock_slack):
        record = _make_record()
        _setup_incident(mock_get_one)
        _setup_session(mock_session, record)
        mock_post.return_value = _resp({})

        PhareIncidentUpdate.update("C123", "Root cause found", "identified")

        mock_post.assert_called_once_with(
            "https://api.phare.io/uptime/incidents/99/updates",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
            json={"state": "identified", "content": "Root cause found"},
        )
        self.assertEqual(len(record.updates), 1)
        self.assertEqual(record.updates[0]["state"], "identified")
        self.assertEqual(record.updates[0]["content"], "Root cause found")

    @patch("incidentbot.phare.handler.slack_web_client")
    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.requests.post")
    def test_resolved_calls_recover_endpoint(self, mock_post, mock_get_one, mock_session, mock_slack):
        record = _make_record()
        _setup_incident(mock_get_one)
        _setup_session(mock_session, record)
        mock_post.return_value = _resp({})

        PhareIncidentUpdate.update("C123", "", "resolved")

        mock_post.assert_called_once_with(
            "https://api.phare.io/uptime/incidents/99/recover",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
        )

    @patch("incidentbot.phare.handler.slack_web_client")
    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.requests.post")
    def test_api_error_does_not_raise(self, mock_post, mock_get_one, mock_session, mock_slack):
        record = _make_record()
        _setup_incident(mock_get_one)
        _setup_session(mock_session, record)
        mock_post.return_value.raise_for_status.side_effect = Exception("503")

        PhareIncidentUpdate.update("C123", "update", "monitoring")  # must not raise


# ---------------------------------------------------------------------------
# PhareIncidentUpdate.update_impact
# ---------------------------------------------------------------------------

class TestPhareIncidentUpdateImpact(unittest.TestCase):
    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.requests.post")
    def test_posts_partial_update(self, mock_post, mock_get_one, mock_session):
        mock_post.return_value = _resp({})
        record = _make_record()
        _setup_incident(mock_get_one)
        _setup_session(mock_session, record)

        PhareIncidentUpdate.update_impact("C123", "partial_outage")

        mock_post.assert_called_once_with(
            "https://api.phare.io/uptime/incidents/99",
            headers={"Authorization": "Bearer test-api-key", "X-Phare-Project-Id": "proj-123"},
            json={"impact": "partial_outage"},
        )

    @patch("incidentbot.phare.handler.Session")
    @patch("incidentbot.phare.handler.IncidentDatabaseInterface.get_one")
    @patch("incidentbot.phare.handler.requests.post")
    def test_api_error_does_not_raise(self, mock_post, mock_get_one, mock_session):
        mock_post.return_value.raise_for_status.side_effect = Exception("500")
        record = _make_record()
        _setup_incident(mock_get_one)
        _setup_session(mock_session, record)

        PhareIncidentUpdate.update_impact("C123", "major_outage")  # must not raise


# ---------------------------------------------------------------------------
# parse_modal_values — checkboxes case
# ---------------------------------------------------------------------------

class TestParseModalValuesCheckboxes(unittest.TestCase):
    def _body(self, selected_values):
        return {
            "view": {
                "blocks": [],
                "state": {
                    "values": {
                        "phare_exclude_from_downtime": {
                            "phare.exclude_from_downtime": {
                                "type": "checkboxes",
                                "selected_options": [
                                    {"value": v} for v in selected_values
                                ],
                            }
                        }
                    }
                },
            }
        }

    def test_checked_returns_value(self):
        result = parse_modal_values(self._body(["exclude"]))
        self.assertEqual(result["phare.exclude_from_downtime"], ["exclude"])

    def test_unchecked_returns_empty_list(self):
        result = parse_modal_values(self._body([]))
        self.assertEqual(result["phare.exclude_from_downtime"], [])

    def test_exclude_from_downtime_bool_derivation(self):
        checked = parse_modal_values(self._body(["exclude"]))
        unchecked = parse_modal_values(self._body([]))
        self.assertTrue("exclude" in (checked.get("phare.exclude_from_downtime") or []))
        self.assertFalse("exclude" in (unchecked.get("phare.exclude_from_downtime") or []))


if __name__ == "__main__":
    unittest.main()
