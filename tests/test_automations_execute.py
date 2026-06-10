"""
Tests for automation action execution in incidentbot/incident/automations.py
"""
from unittest.mock import MagicMock, patch

_mock_settings = MagicMock()
_mock_settings.IS_TEST_ENVIRONMENT = True
_mock_settings.DATABASE_URI = "sqlite:///:memory:"
_mock_settings.SLACK_BOT_TOKEN = "xoxb-test"
_mock_settings.LOG_LEVEL = "INFO"
_mock_settings.automations = []

with (
    patch("incidentbot.configuration.settings.settings", _mock_settings),
    patch("sqlmodel.create_engine", return_value=MagicMock()),
    patch("slack_sdk.WebClient", return_value=MagicMock()),
):
    from incidentbot.incident.automations import _execute, _invite_group, _invite_user, _page_pagerduty, _post_message


def _make_record(channel_id="C123", channel_name="inc-test", slug="inc-test", status="investigating"):
    r = MagicMock()
    r.id = 1
    r.channel_id = channel_id
    r.channel_name = channel_name
    r.slug = slug
    r.status = status
    return r


def _make_action(type, **kwargs):
    action = MagicMock()
    action.type = type
    for k, v in kwargs.items():
        setattr(action, k, v)
    return action


class TestExecuteDispatch:
    def test_dispatches_invite_group(self):
        action = _make_action("invite_group", name="oncall")
        record = _make_record()
        with patch("incidentbot.incident.automations._invite_group") as mock_fn:
            _execute(action, record)
        mock_fn.assert_called_once_with(action, record)

    def test_dispatches_invite_user(self):
        action = _make_action("invite_user", user="U999")
        record = _make_record()
        with patch("incidentbot.incident.automations._invite_user") as mock_fn:
            _execute(action, record)
        mock_fn.assert_called_once_with(action, record)

    def test_dispatches_page_pagerduty(self):
        action = _make_action("page_pagerduty", escalation_policy="pol-1")
        record = _make_record()
        with patch("incidentbot.incident.automations._page_pagerduty") as mock_fn:
            _execute(action, record)
        mock_fn.assert_called_once_with(action, record)

    def test_dispatches_post_message(self):
        action = _make_action("post_message", message="hi")
        record = _make_record()
        with patch("incidentbot.incident.automations._post_message") as mock_fn:
            _execute(action, record)
        mock_fn.assert_called_once_with(action, record)

    def test_logs_warning_for_unknown_type(self):
        action = _make_action("unknown_type")
        record = _make_record()
        with patch("incidentbot.incident.automations.logger") as mock_log:
            _execute(action, record)
        mock_log.warning.assert_called_once()


class TestInviteGroup:
    def test_invites_members_and_logs_event(self):
        action = _make_action("invite_group", name="oncall-team")
        record = _make_record()
        mock_adapter = MagicMock()
        mock_adapter.get_group_members_by_name.return_value = ["U001", "U002"]

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.EventLogHandler") as mock_log,
        ):
            _invite_group(action, record)

        mock_adapter.invite_users.assert_called_once_with(room_id="C123", user_ids=["U001", "U002"])
        mock_log.create.assert_called_once()

    def test_logs_warning_when_group_empty(self):
        action = _make_action("invite_group", name="empty-group")
        record = _make_record()
        mock_adapter = MagicMock()
        mock_adapter.get_group_members_by_name.return_value = []

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.logger") as mock_log,
        ):
            _invite_group(action, record)

        mock_log.warning.assert_called_once()
        mock_adapter.invite_users.assert_not_called()

    def test_logs_warning_when_group_not_found(self):
        action = _make_action("invite_group", name="missing-group")
        record = _make_record()
        mock_adapter = MagicMock()
        mock_adapter.get_group_members_by_name.return_value = None

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.logger") as mock_log,
        ):
            _invite_group(action, record)

        mock_log.warning.assert_called_once()


class TestInviteUser:
    def test_invites_user_and_logs_event(self):
        action = _make_action("invite_user", user="U999")
        record = _make_record()
        mock_adapter = MagicMock()

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.EventLogHandler") as mock_log,
        ):
            _invite_user(action, record)

        mock_adapter.invite_user.assert_called_once_with(room_id="C123", user_id="U999")
        mock_log.create.assert_called_once()

    def test_logs_warning_when_no_user_configured(self):
        action = _make_action("invite_user", user=None)
        record = _make_record()
        mock_adapter = MagicMock()

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.logger") as mock_log,
        ):
            _invite_user(action, record)

        mock_log.warning.assert_called_once()
        mock_adapter.invite_user.assert_not_called()

    def test_logs_exception_on_failure(self):
        action = _make_action("invite_user", user="U999")
        record = _make_record()
        mock_adapter = MagicMock()
        mock_adapter.invite_user.side_effect = Exception("boom")

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.logger") as mock_log,
        ):
            _invite_user(action, record)

        mock_log.exception.assert_called_once()


class TestPagePagerDuty:
    def test_logs_warning_when_pagerduty_not_enabled(self):
        action = _make_action("page_pagerduty", escalation_policy="pol-1", priority="high")
        record = _make_record()
        _mock_settings.integrations = None

        with patch("incidentbot.incident.automations.logger") as mock_log:
            _page_pagerduty(action, record)

        mock_log.warning.assert_called_once()

    def test_pages_when_integration_enabled(self):
        action = _make_action("page_pagerduty", escalation_policy="pol-1", priority="high")
        record = _make_record()

        mock_pd = MagicMock()
        mock_integrations = MagicMock()
        mock_integrations.pagerduty.enabled = True

        with (
            patch("incidentbot.incident.automations.settings") as mock_s,
            patch("incidentbot.incident.automations.PagerDutyInterface", return_value=mock_pd),
            patch("incidentbot.incident.automations.EventLogHandler"),
        ):
            mock_s.integrations = mock_integrations
            _page_pagerduty(action, record)

        mock_pd.page.assert_called_once()


class TestPostMessage:
    def test_sends_text_via_adapter(self):
        action = _make_action("post_message", message="Incident declared!")
        record = _make_record()
        mock_adapter = MagicMock()

        with patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter):
            _post_message(action, record)

        mock_adapter.send_text.assert_called_once_with(
            room_id="C123", text="Incident declared!"
        )

    def test_logs_exception_on_failure(self):
        action = _make_action("post_message", message="hi")
        record = _make_record()
        mock_adapter = MagicMock()
        mock_adapter.send_text.side_effect = Exception("boom")

        with (
            patch("incidentbot.incident.automations.get_adapter", return_value=mock_adapter),
            patch("incidentbot.incident.automations.logger") as mock_log,
        ):
            _post_message(action, record)

        mock_log.exception.assert_called_once()
