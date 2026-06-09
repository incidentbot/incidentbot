"""
Tests for reminder execution functions in incidentbot/incident/reminders.py
"""
import sys
from unittest.mock import MagicMock, patch

# Evict the module so this file always gets a fresh import with its own
# _mock_settings (other test files import incidentbot.incident.actions, which
# pulls in reminders as a side-effect and leaves it with incompatible settings).
sys.modules.pop("incidentbot.incident.reminders", None)

_mock_settings = MagicMock()
_mock_settings.IS_TEST_ENVIRONMENT = True
_mock_settings.DATABASE_URI = "sqlite:///:memory:"
_mock_settings.SLACK_BOT_TOKEN = "xoxb-test"
_mock_settings.LOG_LEVEL = "INFO"
_mock_settings.options.timezone = "UTC"

_reminder = MagicMock()
_reminder.id = "comms_reminder"
_reminder.enabled = True
_reminder.message = "Time to update?"
_reminder.once = False
_reminder.conditions = None

_mock_settings.reminders = [_reminder]

with (
    patch("incidentbot.configuration.settings.settings", _mock_settings),
    patch("sqlmodel.create_engine", return_value=MagicMock()),
    patch("slack_sdk.WebClient", return_value=MagicMock()),
):
    from incidentbot.incident.reminders import (
        _job_id,
        cancel_reminder_jobs,
        handle_dismiss,
        handle_snooze,
        register_reminder_jobs,
        run_reminder,
    )


def _make_record(channel_id="C123", slug="inc-test"):
    r = MagicMock()
    r.channel_id = channel_id
    r.slug = slug
    r.id = 1
    return r


class TestJobId:
    def test_format(self):
        assert _job_id("inc-test", "comms_reminder") == "inc-test_comms_reminder"


class TestRunReminder:
    def test_posts_message_when_conditions_pass(self):
        record = _make_record()
        mock_client = MagicMock()
        mock_blocks = MagicMock()

        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.evaluate", return_value=True),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
            patch("incidentbot.incident.reminders.BlockBuilder") as mock_bb,
        ):
            mock_bb.reminder_message.return_value = mock_blocks
            run_reminder("C123", "comms_reminder")

        mock_client.chat_postMessage.assert_called_once()

    def test_returns_early_when_reminder_not_found(self):
        mock_client = MagicMock()
        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one") as mock_db,
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            run_reminder("C123", "nonexistent_reminder")
        mock_db.assert_not_called()
        mock_client.chat_postMessage.assert_not_called()

    def test_returns_early_when_reminder_disabled(self):
        _reminder.enabled = False
        mock_client = MagicMock()
        with patch("incidentbot.incident.reminders.slack_web_client", mock_client):
            run_reminder("C123", "comms_reminder")
        mock_client.chat_postMessage.assert_not_called()
        _reminder.enabled = True  # restore

    def test_returns_early_when_incident_not_found(self):
        mock_client = MagicMock()
        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=None),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            run_reminder("C123", "comms_reminder")
        mock_client.chat_postMessage.assert_not_called()

    def test_returns_early_when_condition_fails(self):
        record = _make_record()
        mock_client = MagicMock()
        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.evaluate", return_value=False),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            run_reminder("C123", "comms_reminder")
        mock_client.chat_postMessage.assert_not_called()

    def test_deletes_job_when_once_is_true(self):
        _reminder.once = True
        record = _make_record()
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "inc-test_comms_reminder"

        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.evaluate", return_value=True),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
            patch("incidentbot.incident.reminders.BlockBuilder"),
            patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched,
        ):
            mock_sched.get_job.return_value = mock_job
            run_reminder("C123", "comms_reminder")
            mock_sched.delete_job.assert_called_once_with(mock_job.id)

        _reminder.once = False  # restore

    def test_does_not_delete_job_when_once_is_false(self):
        record = _make_record()
        mock_client = MagicMock()

        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.evaluate", return_value=True),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
            patch("incidentbot.incident.reminders.BlockBuilder"),
            patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched,
        ):
            run_reminder("C123", "comms_reminder")
            mock_sched.delete_job.assert_not_called()


class TestRegisterReminderJobs:
    def test_registers_job_for_enabled_reminder(self):
        record = _make_record()
        with patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched:
            register_reminder_jobs(record)
        mock_sched.scheduler.add_job.assert_called_once()
        call_kwargs = mock_sched.scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "inc-test_comms_reminder"
        assert call_kwargs["minutes"] == _reminder.interval_minutes

    def test_skips_disabled_reminders(self):
        _reminder.enabled = False
        record = _make_record()
        with patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched:
            register_reminder_jobs(record)
        mock_sched.scheduler.add_job.assert_not_called()
        _reminder.enabled = True  # restore


class TestCancelReminderJobs:
    def test_deletes_existing_jobs(self):
        mock_job = MagicMock()
        mock_job.id = "inc-test_comms_reminder"
        with patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched:
            mock_sched.get_job.return_value = mock_job
            cancel_reminder_jobs("inc-test")
        mock_sched.delete_job.assert_called_once_with(job_to_delete=mock_job.id)

    def test_skips_when_job_not_found(self):
        with patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched:
            mock_sched.get_job.return_value = None
            cancel_reminder_jobs("inc-test")
        mock_sched.delete_job.assert_not_called()


class TestHandleSnooze:
    def test_reschedules_job_and_posts_ack(self):
        record = _make_record()
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "inc-test_comms_reminder"

        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched,
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            mock_sched.get_job.return_value = mock_job
            handle_snooze("C123", "comms_reminder", 30, "ts-123")

        mock_sched.reschedule_job.assert_called_once_with(job_id=mock_job.id, new_minutes=30)
        mock_client.chat_postMessage.assert_called_once()
        mock_client.chat_delete.assert_called_once_with(channel="C123", ts="ts-123")

    def test_returns_early_when_incident_not_found(self):
        mock_client = MagicMock()
        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=None),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            handle_snooze("C123", "comms_reminder", 30, "ts-123")
        mock_client.chat_postMessage.assert_not_called()


class TestHandleDismiss:
    def test_deletes_job_and_posts_ack(self):
        record = _make_record()
        mock_client = MagicMock()
        mock_job = MagicMock()
        mock_job.id = "inc-test_comms_reminder"

        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=record),
            patch("incidentbot.incident.reminders.TaskScheduler") as mock_sched,
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            mock_sched.get_job.return_value = mock_job
            handle_dismiss("C123", "comms_reminder", "ts-456")

        mock_sched.delete_job.assert_called_once_with(job_to_delete=mock_job.id)
        mock_client.chat_postMessage.assert_called_once()
        mock_client.chat_delete.assert_called_once_with(channel="C123", ts="ts-456")

    def test_returns_early_when_incident_not_found(self):
        mock_client = MagicMock()
        with (
            patch("incidentbot.incident.reminders.IncidentDatabaseInterface.get_one", return_value=None),
            patch("incidentbot.incident.reminders.slack_web_client", mock_client),
        ):
            handle_dismiss("C123", "comms_reminder", "ts-456")
        mock_client.chat_postMessage.assert_not_called()
