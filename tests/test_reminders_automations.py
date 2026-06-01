"""
Tests for the config-driven reminders and automations system.
"""

from unittest.mock import MagicMock, patch

from incidentbot.configuration.schema import (
    Automation,
    AutomationAction,
    Conditions,
    Jobs,
    PagerDutyOCJob,
    Reminder,
    ReminderAction,
    SlackCacheJob,
    ScrapeForAgingIncidentsJob,
)
from incidentbot.incident.conditions import evaluate


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_record(severity="sev2", status="investigating", participants=None):
    record = MagicMock()
    record.severity = severity
    record.status = status
    record.slug = "inc-test"
    record.channel_id = "C123"
    record.channel_name = "inc-test"
    record.id = 1
    # list_participants is called on the interface, not on record; patch separately
    return record


# ── Conditions ────────────────────────────────────────────────────────────────


class TestEvaluate:
    def test_none_conditions_always_passes(self):
        assert evaluate(None, _make_record()) is True

    def test_empty_conditions_always_passes(self):
        assert evaluate(Conditions(), _make_record()) is True

    def test_severity_is_match(self):
        cond = Conditions(severity_is=["sev1", "sev2"])
        assert evaluate(cond, _make_record(severity="sev1")) is True
        assert evaluate(cond, _make_record(severity="sev2")) is True

    def test_severity_is_no_match(self):
        cond = Conditions(severity_is=["sev1"])
        assert evaluate(cond, _make_record(severity="sev2")) is False

    def test_status_is_match(self):
        cond = Conditions(status_is=["investigating", "identified"])
        assert evaluate(cond, _make_record(status="investigating")) is True

    def test_status_is_no_match(self):
        cond = Conditions(status_is=["investigating"])
        assert evaluate(cond, _make_record(status="resolved")) is False

    def test_status_is_final_true(self):
        cond = Conditions(status_is_final=True)
        record = _make_record(status="resolved")
        mock_statuses = {
            "investigating": MagicMock(final=False),
            "resolved": MagicMock(final=True),
        }
        with patch(
            "incidentbot.incident.conditions.settings"
        ) as mock_settings:
            mock_settings.statuses = mock_statuses
            assert evaluate(cond, record) is True

    def test_status_is_final_false(self):
        cond = Conditions(status_is_final=True)
        record = _make_record(status="investigating")
        mock_statuses = {
            "investigating": MagicMock(final=False),
            "resolved": MagicMock(final=True),
        }
        with patch(
            "incidentbot.incident.conditions.settings"
        ) as mock_settings:
            mock_settings.statuses = mock_statuses
            assert evaluate(cond, record) is False

    def test_no_roles_claimed_passes_when_empty(self):
        cond = Conditions(no_roles_claimed=True)
        record = _make_record()
        with patch(
            "incidentbot.incident.conditions.IncidentDatabaseInterface"
        ) as mock_db:
            mock_db.list_participants.return_value = []
            assert evaluate(cond, record) is True

    def test_no_roles_claimed_fails_when_assigned(self):
        cond = Conditions(no_roles_claimed=True)
        record = _make_record()
        with patch(
            "incidentbot.incident.conditions.IncidentDatabaseInterface"
        ) as mock_db:
            mock_db.list_participants.return_value = [MagicMock()]
            assert evaluate(cond, record) is False

    def test_multiple_conditions_all_must_pass(self):
        cond = Conditions(severity_is=["sev1"], status_is=["investigating"])
        assert evaluate(cond, _make_record(severity="sev1", status="investigating")) is True
        assert evaluate(cond, _make_record(severity="sev2", status="investigating")) is False
        assert evaluate(cond, _make_record(severity="sev1", status="resolved")) is False


# ── Schema ────────────────────────────────────────────────────────────────────


class TestReminderSchema:
    def test_default_reminder(self):
        r = Reminder(
            id="test",
            message="hello",
            interval_minutes=30,
        )
        assert r.enabled is True
        assert r.once is False
        assert r.conditions is None
        assert r.include_role_buttons is False

    def test_reminder_with_conditions(self):
        r = Reminder(
            id="role_watcher",
            message="claim roles",
            interval_minutes=10,
            once=True,
            conditions=Conditions(no_roles_claimed=True),
            include_role_buttons=True,
            actions=[ReminderAction(type="dismiss", label="Dismiss")],
        )
        assert r.once is True
        assert r.conditions.no_roles_claimed is True
        assert r.include_role_buttons is True

    def test_snooze_action_has_intervals(self):
        a = ReminderAction(type="snooze", intervals=[30, 60, 90])
        assert a.intervals == [30, 60, 90]


class TestAutomationSchema:
    def test_automation_defaults(self):
        a = Automation(
            id="test",
            trigger="on_open",
            actions=[AutomationAction(type="post_message", message="hi")],
        )
        assert a.enabled is True
        assert a.conditions is None

    def test_automation_with_severity_condition(self):
        a = Automation(
            id="page_sev1",
            trigger="on_open",
            conditions=Conditions(severity_is=["sev1"]),
            actions=[
                AutomationAction(
                    type="page_pagerduty",
                    escalation_policy="pol-123",
                    priority="high",
                )
            ],
        )
        assert a.conditions.severity_is == ["sev1"]
        assert a.actions[0].escalation_policy == "pol-123"


class TestJobsSchema:
    def test_defaults(self):
        j = Jobs()
        assert j.scrape_for_aging_incidents.enabled is True
        assert j.scrape_for_aging_incidents.interval_days == 2
        assert j.scrape_for_aging_incidents.max_age_days == 7
        assert j.update_slack_cache.enabled is True
        assert j.update_slack_cache.interval_minutes == 15
        assert j.update_pagerduty_oc_data.enabled is True
        assert j.update_pagerduty_oc_data.interval_minutes == 30

    def test_override(self):
        j = Jobs(
            scrape_for_aging_incidents=ScrapeForAgingIncidentsJob(interval_days=5, max_age_days=14),
            update_slack_cache=SlackCacheJob(interval_minutes=60),
        )
        assert j.scrape_for_aging_incidents.interval_days == 5
        assert j.scrape_for_aging_incidents.max_age_days == 14
        assert j.update_slack_cache.interval_minutes == 60

    def test_jobs_can_be_disabled(self):
        j = Jobs(
            update_slack_cache=SlackCacheJob(enabled=False),
            update_pagerduty_oc_data=PagerDutyOCJob(enabled=False),
        )
        assert j.update_slack_cache.enabled is False
        assert j.update_pagerduty_oc_data.enabled is False


# ── Automations dispatcher ────────────────────────────────────────────────────


class TestRunAutomations:
    def _make_automation(self, trigger, action_type="post_message", conditions=None):
        return Automation(
            id=f"auto_{trigger}",
            trigger=trigger,
            conditions=conditions,
            actions=[AutomationAction(type=action_type, message="test")],
        )

    def test_skips_disabled_automation(self):
        auto = self._make_automation("on_open")
        auto.enabled = False
        record = _make_record()

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec:
            mock_s.automations = [auto]
            from incidentbot.incident.automations import run
            run("on_open", record)
            mock_exec.assert_not_called()

    def test_fires_matching_trigger(self):
        auto = self._make_automation("on_open")
        record = _make_record()

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec, \
             patch("incidentbot.incident.automations.evaluate", return_value=True):
            mock_s.automations = [auto]
            from incidentbot.incident.automations import run
            run("on_open", record)
            mock_exec.assert_called_once()

    def test_skips_non_matching_trigger(self):
        auto = self._make_automation("on_open")
        record = _make_record()

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec:
            mock_s.automations = [auto]
            from incidentbot.incident.automations import run
            run("on_severity_change", record)
            mock_exec.assert_not_called()

    def test_on_final_status_fires_on_status_change_when_final(self):
        auto = self._make_automation("on_final_status")
        record = _make_record(status="resolved")
        mock_statuses = {
            "resolved": MagicMock(final=True),
            "investigating": MagicMock(final=False),
        }

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec, \
             patch("incidentbot.incident.automations.evaluate", return_value=True):
            mock_s.automations = [auto]
            mock_s.statuses = mock_statuses
            from incidentbot.incident.automations import run
            run("on_status_change", record)
            mock_exec.assert_called_once()

    def test_on_final_status_skips_when_not_final(self):
        auto = self._make_automation("on_final_status")
        record = _make_record(status="investigating")
        mock_statuses = {
            "resolved": MagicMock(final=True),
            "investigating": MagicMock(final=False),
        }

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec:
            mock_s.automations = [auto]
            mock_s.statuses = mock_statuses
            from incidentbot.incident.automations import run
            run("on_status_change", record)
            mock_exec.assert_not_called()

    def test_condition_failure_skips_execution(self):
        auto = self._make_automation(
            "on_open",
            conditions=Conditions(severity_is=["sev1"]),
        )
        record = _make_record(severity="sev3")

        with patch("incidentbot.incident.automations.settings") as mock_s, \
             patch("incidentbot.incident.automations._execute") as mock_exec:
            mock_s.automations = [auto]
            from incidentbot.incident.automations import run
            run("on_open", record)
            mock_exec.assert_not_called()
