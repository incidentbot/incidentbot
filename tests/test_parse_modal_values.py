"""
Tests for incidentbot/slack/util.py :: parse_modal_values

The function is importable via load_module (same pattern used in test_phare_handler.py).
"""
from tests.runtime import load_module

_util = load_module("incidentbot.slack.util")
parse_modal_values = _util.parse_modal_values


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _body(block_id, action_id, content):
    """Build a minimal Slack modal submission body."""
    return {
        "view": {
            "blocks": [{"block_id": block_id}],
            "state": {
                "values": {
                    block_id: {
                        action_id: content,
                    }
                }
            },
        }
    }


# ---------------------------------------------------------------------------
# Plain text input
# ---------------------------------------------------------------------------

class TestPlainTextInput:
    def test_parses_value(self):
        body = _body("description", "incident.description", {
            "type": "plain_text_input",
            "value": "Production database is down",
        })
        result = parse_modal_values(body)
        assert result["incident.description"] == "Production database is down"

    def test_parses_none_value(self):
        body = _body("description", "incident.description", {
            "type": "plain_text_input",
            "value": None,
        })
        result = parse_modal_values(body)
        assert result["incident.description"] is None


# ---------------------------------------------------------------------------
# Static select
# ---------------------------------------------------------------------------

class TestStaticSelect:
    def test_parses_selected_option(self):
        body = _body("severity", "incident.severity", {
            "type": "static_select",
            "selected_option": {"value": "sev2", "text": {"type": "plain_text", "text": "SEV2"}},
        })
        result = parse_modal_values(body)
        assert result["incident.severity"] == "sev2"


# ---------------------------------------------------------------------------
# Multi static select
# ---------------------------------------------------------------------------

class TestMultiStaticSelect:
    def test_parses_multiple_options(self):
        body = _body("components", "incident.components", {
            "type": "multi_static_select",
            "selected_options": [
                {"value": "api"},
                {"value": "database"},
            ],
        })
        result = parse_modal_values(body)
        assert result["incident.components"] == ["api", "database"]

    def test_empty_selection_returns_empty_list(self):
        body = _body("components", "incident.components", {
            "type": "multi_static_select",
            "selected_options": [],
        })
        result = parse_modal_values(body)
        assert result["incident.components"] == []


# ---------------------------------------------------------------------------
# Datepicker
# ---------------------------------------------------------------------------

class TestDatepicker:
    def test_parses_selected_date(self):
        body = _body("date_block", "incident.date", {
            "type": "datepicker",
            "selected_date": "2024-03-15",
        })
        result = parse_modal_values(body)
        assert result["incident.date"] == "2024-03-15"

    def test_none_date(self):
        body = _body("date_block", "incident.date", {
            "type": "datepicker",
            "selected_date": None,
        })
        result = parse_modal_values(body)
        assert result["incident.date"] is None


# ---------------------------------------------------------------------------
# Timepicker
# ---------------------------------------------------------------------------

class TestTimepicker:
    def test_parses_selected_time(self):
        body = _body("time_block", "incident.time", {
            "type": "timepicker",
            "selected_time": "14:30",
        })
        result = parse_modal_values(body)
        assert result["incident.time"] == "14:30"


# ---------------------------------------------------------------------------
# Users select
# ---------------------------------------------------------------------------

class TestUsersSelect:
    def test_parses_selected_user(self):
        body = _body("user_block", "incident.user", {
            "type": "users_select",
            "selected_user": "U12345",
        })
        result = parse_modal_values(body)
        assert result["incident.user"] == "U12345"


# ---------------------------------------------------------------------------
# Multi conversations select
# ---------------------------------------------------------------------------

class TestMultiConversationsSelect:
    def test_parses_selected_conversations(self):
        body = _body("convos", "incident.channels", {
            "type": "multi_conversations_select",
            "selected_conversations": ["C111", "C222"],
        })
        result = parse_modal_values(body)
        assert result["incident.channels"] == ["C111", "C222"]


# ---------------------------------------------------------------------------
# Checkboxes (already covered via phare tests — additional branches here)
# ---------------------------------------------------------------------------

class TestCheckboxes:
    def test_checked_options(self):
        body = _body("opts", "incident.opts", {
            "type": "checkboxes",
            "selected_options": [{"value": "opt_a"}, {"value": "opt_b"}],
        })
        result = parse_modal_values(body)
        assert result["incident.opts"] == ["opt_a", "opt_b"]

    def test_no_checked_options(self):
        body = _body("opts", "incident.opts", {
            "type": "checkboxes",
            "selected_options": [],
        })
        result = parse_modal_values(body)
        assert result["incident.opts"] == []


# ---------------------------------------------------------------------------
# Multiple blocks in a single submission
# ---------------------------------------------------------------------------

class TestMultipleBlocks:
    def test_parses_multiple_blocks(self):
        body = {
            "view": {
                "blocks": [
                    {"block_id": "b1"},
                    {"block_id": "b2"},
                ],
                "state": {
                    "values": {
                        "b1": {
                            "action1": {"type": "plain_text_input", "value": "hello"},
                        },
                        "b2": {
                            "action2": {
                                "type": "static_select",
                                "selected_option": {"value": "sev1"},
                            }
                        },
                    }
                },
            }
        }
        result = parse_modal_values(body)
        assert result["action1"] == "hello"
        assert result["action2"] == "sev1"


# ---------------------------------------------------------------------------
# by_block_id mode
# ---------------------------------------------------------------------------

class TestByBlockId:
    def _multi_block_body(self):
        return {
            "view": {
                "blocks": [
                    {"block_id": "target_block", "type": "section"},
                    {"block_id": "other_block", "type": "actions"},
                ],
                "state": {"values": {}},
            }
        }

    def test_returns_block_when_found(self):
        body = self._multi_block_body()
        result = parse_modal_values(body, by_block_id=True, by_block_id_name="target_block")
        assert result is not None
        assert result["block_id"] == "target_block"

    def test_returns_empty_when_block_not_found(self):
        # When the named block doesn't exist the main values loop runs but finds
        # nothing (values dict is empty), so the function returns an empty dict.
        body = self._multi_block_body()
        result = parse_modal_values(body, by_block_id=True, by_block_id_name="missing_block")
        assert not result  # {} is falsy

    def test_returns_none_when_no_name_provided(self):
        body = self._multi_block_body()
        result = parse_modal_values(body, by_block_id=True, by_block_id_name=None)
        assert result is None
