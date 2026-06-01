"""
Tests for incidentbot/configuration/schema.py

Schema models are pure Pydantic classes — no I/O, no mocking needed.
"""
import pytest
from pydantic import ValidationError

from incidentbot.configuration.schema import (
    GitlabIntegration,
    StatusDefinition,
    RoleDefinition,
    Options,
    AdditionalWelcomeMessage,
)

# ---------------------------------------------------------------------------
# GitlabIntegration._validate_issue_type
# ---------------------------------------------------------------------------

_GITLAB_BASE = dict(
    enabled=True,
    project_id=1,
    status_mapping=[],
    severity_mapping=[],
    issue_types=[],
)


class TestGitlabIssueTypeValidator:
    def test_incident_is_valid(self):
        obj = GitlabIntegration(**{**_GITLAB_BASE, "issue_type": "incident"})
        assert obj.issue_type == "incident"

    def test_issue_is_valid(self):
        obj = GitlabIntegration(**{**_GITLAB_BASE, "issue_type": "issue"})
        assert obj.issue_type == "issue"

    def test_none_is_allowed(self):
        obj = GitlabIntegration(**{**_GITLAB_BASE, "issue_type": None})
        assert obj.issue_type is None

    def test_default_is_incident(self):
        obj = GitlabIntegration(**_GITLAB_BASE)
        assert obj.issue_type == "incident"

    def test_invalid_value_raises_validation_error(self):
        with pytest.raises(ValidationError, match="issue_type must be either"):
            GitlabIntegration(**{**_GITLAB_BASE, "issue_type": "task"})

    def test_empty_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            GitlabIntegration(**{**_GITLAB_BASE, "issue_type": ""})


# ---------------------------------------------------------------------------
# StatusDefinition
# ---------------------------------------------------------------------------


class TestStatusDefinition:
    def test_defaults_are_false(self):
        s = StatusDefinition()
        assert s.initial is False
        assert s.final is False

    def test_can_set_initial(self):
        s = StatusDefinition(initial=True)
        assert s.initial is True
        assert s.final is False

    def test_can_set_final(self):
        s = StatusDefinition(final=True)
        assert s.final is True
        assert s.initial is False


# ---------------------------------------------------------------------------
# RoleDefinition
# ---------------------------------------------------------------------------


class TestRoleDefinition:
    def test_required_fields(self):
        r = RoleDefinition(description="Leads the incident response")
        assert r.description == "Leads the incident response"
        assert r.is_lead is False

    def test_is_lead_override(self):
        r = RoleDefinition(description="Commander", is_lead=True)
        assert r.is_lead is True


# ---------------------------------------------------------------------------
# Options defaults
# ---------------------------------------------------------------------------


class TestOptionsDefaults:
    def test_default_channel_prefix(self):
        o = Options()
        assert o.channel_name_prefix == "inc"

    def test_default_timezone(self):
        o = Options()
        assert o.timezone == "UTC"

    def test_default_pagination(self):
        o = Options()
        assert o.slack_items_pagination_per_page == 5

    def test_meeting_link_defaults_to_none(self):
        o = Options()
        assert o.meeting_link is None


# ---------------------------------------------------------------------------
# AdditionalWelcomeMessage
# ---------------------------------------------------------------------------


class TestAdditionalWelcomeMessage:
    def test_pin_defaults_to_false(self):
        m = AdditionalWelcomeMessage(message="Hello!")
        assert m.message == "Hello!"
        assert m.pin is False

    def test_pin_can_be_set(self):
        m = AdditionalWelcomeMessage(message="Hello!", pin=True)
        assert m.pin is True
