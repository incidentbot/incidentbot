"""
Tests for the pure BlockBuilder and IncidentUpdate methods in
incidentbot/slack/messages.py.

These methods build Slack Block Kit JSON without side effects — we just assert
the structural shape and key values of the output.

NOTE: Multiple test files reload incidentbot.slack.messages via load_module, so
the module's ``settings`` binding can change between collection and test
execution. We use a module-scoped autouse fixture to re-establish settings
before every test in this file.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from tests.runtime import load_module


# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

_ICONS = {
    "slack": {
        "postmortem": ":book:",
        "update": ":mega:",
        "channel": ":speech_balloon:",
        "role": ":bust_in_silhouette:",
        "severity": ":rotating_light:",
        "status": ":traffic_light:",
        "description": ":memo:",
        "components": ":jigsaw:",
    }
}

_STATUSES = {
    "investigating": SimpleNamespace(final=False, initial=True),
    "identified": SimpleNamespace(final=False, initial=False),
    "resolved": SimpleNamespace(final=True, initial=False),
}

_ROLES = {
    "incident_commander": SimpleNamespace(
        description="Leads the incident response", is_lead=True
    ),
    "communications_lead": SimpleNamespace(
        description="Handles external comms", is_lead=False
    ),
}

_SEVERITIES = {
    "sev1": "Critical — major impact",
    "sev2": "High — significant impact",
}

# Load the module once (may be reloaded by other test files, but we patch per-test)
messages = load_module(
    "incidentbot.slack.messages",
    statuses=_STATUSES,
    icons=_ICONS,
    links=None,
)

BlockBuilder = messages.BlockBuilder
IncidentUpdate = messages.IncidentUpdate


def _make_settings():
    """Return a fully configured MagicMock settings object for messages tests."""
    s = MagicMock()
    s.platform = "slack"
    s.icons = _ICONS
    s.statuses = _STATUSES
    s.severities = _SEVERITIES
    s.roles = _ROLES
    s.root_slash_command = "/inc"
    s.links = None
    # gitlab_incident_message accesses integrations.gitlab.issue_type
    s.integrations = MagicMock()
    s.integrations.gitlab = MagicMock()
    s.integrations.gitlab.issue_type = "incident"
    return s


@pytest.fixture(autouse=True)
def _patch_messages_settings():
    """
    Patch the settings object in the messages module before each test.

    Because other test files may reload incidentbot.slack.messages (via
    load_module), the module-level settings reference can change. This fixture
    ensures our tests always see a correctly configured settings.
    """
    with patch.object(messages, "settings", _make_settings()):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _action_ids(blocks: list[dict]) -> list[str]:
    ids = []
    for block in blocks:
        if block.get("type") != "actions":
            continue
        for el in block.get("elements", []):
            if el.get("action_id"):
                ids.append(el["action_id"])
    return ids


def _block_types(blocks: list[dict]) -> list[str]:
    return [b.get("type") for b in blocks]


def _find_block(blocks, block_type=None, block_id=None):
    for b in blocks:
        if block_type and b.get("type") != block_type:
            continue
        if block_id and b.get("block_id") != block_id:
            continue
        return b
    return None


def _mock_job(job_id: str, name: str) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.name = name
    return job


# ---------------------------------------------------------------------------
# reminder_message
# ---------------------------------------------------------------------------

class TestReminderMessage:
    def _comms_reminder(self):
        from incidentbot.configuration.schema import Reminder, ReminderAction
        return Reminder(
            id="comms_reminder",
            message="Time to send a status update?",
            interval_minutes=30,
            actions=[
                ReminderAction(type="send_update", label="Send Update"),
                ReminderAction(type="snooze", intervals=[30, 60, 90]),
                ReminderAction(type="dismiss", label="Stop Reminders"),
            ],
        )

    def test_returns_list(self):
        blocks = BlockBuilder.reminder_message(self._comms_reminder(), slug="inc-123")
        assert isinstance(blocks, list)

    def test_has_section_and_actions(self):
        blocks = BlockBuilder.reminder_message(self._comms_reminder(), slug="inc-123")
        types = _block_types(blocks)
        assert "section" in types
        assert "actions" in types

    def test_snooze_action_ids_present(self):
        blocks = BlockBuilder.reminder_message(self._comms_reminder(), slug="inc-123")
        ids = _action_ids(blocks)
        assert any("reminder.snooze.comms_reminder" in id for id in ids)

    def test_dismiss_action_id_present(self):
        blocks = BlockBuilder.reminder_message(self._comms_reminder(), slug="inc-123")
        ids = _action_ids(blocks)
        assert "reminder.dismiss.comms_reminder" in ids

    def test_message_text_in_section(self):
        blocks = BlockBuilder.reminder_message(self._comms_reminder(), slug="inc-123")
        texts = [b.get("text", {}).get("text", "") for b in blocks if b.get("type") == "section"]
        assert any("status update" in t for t in texts)


# ---------------------------------------------------------------------------
# help_message
# ---------------------------------------------------------------------------

class TestHelpMessage:
    def test_returns_list(self):
        blocks = BlockBuilder.help_message()
        assert isinstance(blocks, list)

    def test_contains_header(self):
        blocks = BlockBuilder.help_message()
        assert "header" in _block_types(blocks)

    def test_contains_section_with_command(self):
        blocks = BlockBuilder.help_message()
        text_content = " ".join(
            b.get("text", {}).get("text", "")
            for b in blocks
            if b.get("type") == "section"
        )
        assert "/inc" in text_content


# ---------------------------------------------------------------------------
# jira_issue_message
# ---------------------------------------------------------------------------

class TestJiraIssueMessage:
    def test_returns_list(self):
        blocks = BlockBuilder.jira_issue_message(
            key="INC-123", summary="DB outage", type="Bug", link="https://jira.example.com/INC-123"
        )
        assert isinstance(blocks, list)

    def test_contains_view_issue_action(self):
        blocks = BlockBuilder.jira_issue_message(
            key="INC-123", summary="DB outage", type="Bug", link="https://jira.example.com/INC-123"
        )
        ids = _action_ids(blocks)
        assert "jira.view_issue" in ids

    def test_link_in_button(self):
        link = "https://jira.example.com/INC-123"
        blocks = BlockBuilder.jira_issue_message(
            key="INC-123", summary="DB", type="Bug", link=link
        )
        # Find the button with the link
        actions = _find_block(blocks, block_type="actions")
        assert actions is not None
        button = next(
            (el for el in actions["elements"] if el.get("action_id") == "jira.view_issue"), None
        )
        assert button is not None
        assert button.get("url") == link

    def test_key_and_summary_appear_in_text(self):
        blocks = BlockBuilder.jira_issue_message(
            key="INC-123", summary="Database is on fire", type="Incident",
            link="https://jira.example.com"
        )
        # Jira message uses both "text" and "fields" sections
        all_text = " ".join(
            t
            for b in blocks
            if b.get("type") == "section"
            for t in [
                b.get("text", {}).get("text", ""),
                *(f.get("text", "") for f in (b.get("fields") or [])),
            ]
        )
        assert "INC-123" in all_text
        assert "Database is on fire" in all_text


# ---------------------------------------------------------------------------
# gitlab_incident_message
# ---------------------------------------------------------------------------

class TestGitlabIncidentMessage:
    def test_returns_list(self):
        blocks = BlockBuilder.gitlab_incident_message(
            id="42", summary="API down", link="https://gitlab.example.com/issues/42"
        )
        assert isinstance(blocks, list)

    def test_contains_view_issue_action(self):
        blocks = BlockBuilder.gitlab_incident_message(
            id="42", summary="API down", link="https://gitlab.example.com/issues/42"
        )
        ids = _action_ids(blocks)
        assert "gitlab.view_issue" in ids

    def test_link_in_button(self):
        link = "https://gitlab.example.com/issues/42"
        blocks = BlockBuilder.gitlab_incident_message(id="42", summary="API", link=link)
        actions = _find_block(blocks, block_type="actions")
        button = next(
            (el for el in actions["elements"] if el.get("action_id") == "gitlab.view_issue"), None
        )
        assert button["url"] == link


# ---------------------------------------------------------------------------
# task_list
# ---------------------------------------------------------------------------

class TestTaskList:
    def test_empty_list_returns_informational_blocks(self):
        blocks = BlockBuilder.task_list(tasks=[])
        assert isinstance(blocks, list)
        assert len(blocks) > 0

    def test_returns_list_type(self):
        job = _mock_job("job-1", "my_task")
        blocks = BlockBuilder.task_list(tasks=[job])
        assert isinstance(blocks, list)

    def test_contains_header(self):
        blocks = BlockBuilder.task_list(tasks=[_mock_job("j", "t")])
        assert "header" in _block_types(blocks)

    def test_job_names_appear_in_output(self):
        job = _mock_job("my-job-id", "special_task_name")
        blocks = BlockBuilder.task_list(tasks=[job])
        all_text = " ".join(
            b.get("text", {}).get("text", "")
            for b in blocks
            if b.get("type") in ("section",)
        )
        assert "special_task_name" in all_text or "my-job-id" in all_text


# ---------------------------------------------------------------------------
# reminder_message with include_role_buttons
# ---------------------------------------------------------------------------

class TestRoleWatcherMessage:
    def _role_watcher(self):
        from incidentbot.configuration.schema import Reminder, ReminderAction, Conditions
        return Reminder(
            id="role_watcher",
            message="No roles have been assigned yet.",
            interval_minutes=10,
            once=True,
            conditions=Conditions(no_roles_claimed=True),
            include_role_buttons=True,
            actions=[ReminderAction(type="dismiss", label="Dismiss")],
        )

    def test_returns_list(self):
        blocks = BlockBuilder.reminder_message(self._role_watcher(), slug="inc-123")
        assert isinstance(blocks, list)

    def test_contains_actions_block(self):
        blocks = BlockBuilder.reminder_message(self._role_watcher(), slug="inc-123")
        assert "actions" in _block_types(blocks)

    def test_roles_appear_as_action_ids(self):
        blocks = BlockBuilder.reminder_message(self._role_watcher(), slug="inc-123")
        ids = _action_ids(blocks)
        for role in _ROLES:
            assert any(role in id for id in ids)


# ---------------------------------------------------------------------------
# IncidentUpdate.public_update
# ---------------------------------------------------------------------------

class TestIncidentUpdatePublicUpdate:
    _KWARGS = dict(
        id="C123",
        impacted_resources="API, Database",
        message="We are investigating a database outage.",
        timestamp="2024-03-15T10:00:00",
        user_id="U456",
    )

    def test_returns_list(self):
        blocks = IncidentUpdate.public_update(**self._KWARGS)
        assert isinstance(blocks, list)

    def test_contains_header(self):
        blocks = IncidentUpdate.public_update(**self._KWARGS)
        assert "header" in _block_types(blocks)

    def test_impacted_resources_in_content(self):
        blocks = IncidentUpdate.public_update(**self._KWARGS)
        all_text = " ".join(
            field.get("text", "")
            for b in blocks
            if b.get("type") == "section"
            for field in (b.get("fields") or [b.get("text", {})])
        )
        assert "API, Database" in all_text

    def test_message_in_content(self):
        blocks = IncidentUpdate.public_update(**self._KWARGS)
        all_text = " ".join(
            b.get("text", {}).get("text", "")
            for b in blocks
            if b.get("type") == "section" and "text" in b
        )
        assert "database outage" in all_text

    def test_user_id_in_content(self):
        blocks = IncidentUpdate.public_update(**self._KWARGS)
        all_text = str(blocks)
        assert "U456" in all_text


# ---------------------------------------------------------------------------
# IncidentUpdate.role
# ---------------------------------------------------------------------------

class TestIncidentUpdateRole:
    def test_returns_dict_with_channel_and_blocks(self):
        result = IncidentUpdate.role(
            action="joined", channel="C123", role="incident_commander", user="U456"
        )
        assert isinstance(result, dict)
        assert result["channel"] == "C123"
        assert isinstance(result["blocks"], list)

    def test_contains_header_and_section(self):
        result = IncidentUpdate.role(action="joined", channel="C123", role="commander", user="U999")
        types = _block_types(result["blocks"])
        assert "header" in types
        assert "section" in types

    def test_user_and_role_in_message(self):
        result = IncidentUpdate.role(action="left", channel="C123", role="comms_lead", user="U777")
        section = _find_block(result["blocks"], block_type="section")
        text = section["text"]["text"]
        assert "U777" in text
        assert "comms_lead" in text
        assert "left" in text


# ---------------------------------------------------------------------------
# IncidentUpdate.severity
# ---------------------------------------------------------------------------

class TestIncidentUpdateSeverity:
    def test_returns_dict_with_channel(self):
        result = IncidentUpdate.severity(channel="C123", severity="sev1")
        assert result["channel"] == "C123"
        assert isinstance(result["blocks"], list)

    def test_severity_in_section_text(self):
        result = IncidentUpdate.severity(channel="C123", severity="sev1")
        section = _find_block(result["blocks"], block_type="section")
        assert "SEV1" in section["text"]["text"]

    def test_severity_description_in_text(self):
        result = IncidentUpdate.severity(channel="C123", severity="sev2")
        section = _find_block(result["blocks"], block_type="section")
        assert "significant impact" in section["text"]["text"]


# ---------------------------------------------------------------------------
# IncidentUpdate.status
# ---------------------------------------------------------------------------

class TestIncidentUpdateStatus:
    def test_returns_dict_with_channel(self):
        result = IncidentUpdate.status(channel="C123", status="investigating")
        assert result["channel"] == "C123"
        assert isinstance(result["blocks"], list)

    def test_status_in_section_text(self):
        result = IncidentUpdate.status(channel="C123", status="resolved")
        section = _find_block(result["blocks"], block_type="section")
        assert "Resolved" in section["text"]["text"]

    def test_header_present(self):
        result = IncidentUpdate.status(channel="C123", status="investigating")
        assert "header" in _block_types(result["blocks"])
