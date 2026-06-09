"""
Tests for the pure/near-pure helper functions in incidentbot/incident/actions.py.

Because actions.py has heavy module-level imports (Slack SDK, APScheduler, DB engine),
we import it via the load_module helper which mocks all boot-time dependencies.
The settings object inside the loaded module is then patched per-test as needed.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch


from tests.runtime import load_module

# ---------------------------------------------------------------------------
# Load actions module with boot-time deps mocked
# ---------------------------------------------------------------------------
_actions = load_module("incidentbot.incident.actions")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(
    statuses=None,
    integrations=None,
    pin_content_reacji="pushpin",
    atlassian_api_url=None,
):
    s = MagicMock()
    s.statuses = statuses or {}
    s.integrations = integrations
    s.pin_content_reacji = pin_content_reacji
    if atlassian_api_url is not None:
        s.ATLASSIAN_API_URL = atlassian_api_url
    else:
        del s.ATLASSIAN_API_URL  # ensure getattr returns default
    return s


# ---------------------------------------------------------------------------
# _get_final_statuses / _is_final_status
# ---------------------------------------------------------------------------

class TestFinalStatuses:
    def test_returns_final_statuses(self):
        statuses = {
            "investigating": SimpleNamespace(final=False),
            "resolved": SimpleNamespace(final=True),
        }
        with patch.object(_actions, "settings", _make_settings(statuses=statuses)):
            result = _actions._get_final_statuses()
        assert result == {"resolved"}

    def test_empty_statuses_returns_empty_set(self):
        with patch.object(_actions, "settings", _make_settings(statuses={})):
            result = _actions._get_final_statuses()
        assert result == set()

    def test_multiple_final_statuses(self):
        statuses = {
            "investigating": SimpleNamespace(final=False),
            "resolved": SimpleNamespace(final=True),
            "postmortem": SimpleNamespace(final=True),
        }
        with patch.object(_actions, "settings", _make_settings(statuses=statuses)):
            result = _actions._get_final_statuses()
        assert result == {"resolved", "postmortem"}

    def test_is_final_status_true(self):
        statuses = {"resolved": SimpleNamespace(final=True)}
        with patch.object(_actions, "settings", _make_settings(statuses=statuses)):
            assert _actions._is_final_status("resolved") is True

    def test_is_final_status_false(self):
        statuses = {
            "investigating": SimpleNamespace(final=False),
            "resolved": SimpleNamespace(final=True),
        }
        with patch.object(_actions, "settings", _make_settings(statuses=statuses)):
            assert _actions._is_final_status("investigating") is False

    def test_is_final_status_unknown_status_is_false(self):
        statuses = {"resolved": SimpleNamespace(final=True)}
        with patch.object(_actions, "settings", _make_settings(statuses=statuses)):
            assert _actions._is_final_status("unknown") is False


# ---------------------------------------------------------------------------
# _build_postmortem_title
# ---------------------------------------------------------------------------

class TestBuildPostmortemTitle:
    def test_title_contains_slug_and_description(self):
        incident = SimpleNamespace(slug="inc-2024-001", description="Database outage")
        title = _actions._build_postmortem_title(incident)
        assert "INC-2024-001" in title
        assert "Database outage" in title

    def test_title_contains_date(self):
        import datetime
        incident = SimpleNamespace(slug="inc-001", description="Outage")
        title = _actions._build_postmortem_title(incident)
        today = datetime.datetime.today().strftime("%Y-%m-%d")
        assert today in title

    def test_title_format(self):
        incident = SimpleNamespace(slug="inc-001", description="DB crash")
        title = _actions._build_postmortem_title(incident)
        # Format: "YYYY-MM-DD - INC-001 - DB crash"
        parts = title.split(" - ")
        assert len(parts) == 3
        assert parts[1] == "INC-001"
        assert parts[2] == "DB crash"


# ---------------------------------------------------------------------------
# _is_confluence_postmortem_link
# ---------------------------------------------------------------------------

class TestIsConfluencePostmortemLink:
    def _settings_no_confluence(self):
        return _make_settings(integrations=None)

    def _settings_with_confluence_url(self, url):
        confluence = SimpleNamespace(url=url)
        atlassian = SimpleNamespace(confluence=confluence)
        integrations = SimpleNamespace(atlassian=atlassian)
        s = _make_settings(integrations=integrations)
        # Ensure ATLASSIAN_API_URL is not set (use fallback logic)
        s.ATLASSIAN_API_URL = None
        return s

    def test_none_link_returns_false(self):
        with patch.object(_actions, "settings", self._settings_no_confluence()):
            assert _actions._is_confluence_postmortem_link(None) is False

    def test_empty_string_returns_false(self):
        with patch.object(_actions, "settings", self._settings_no_confluence()):
            assert _actions._is_confluence_postmortem_link("") is False

    def test_atlassian_net_wiki_link_is_confluence(self):
        url = "https://myorg.atlassian.net/wiki/spaces/OPS/pages/12345/My+Page"
        with patch.object(_actions, "settings", self._settings_no_confluence()):
            assert _actions._is_confluence_postmortem_link(url) is True

    def test_gitlab_link_is_not_confluence(self):
        url = "https://gitlab.example.com/group/project/-/issues/42"
        with patch.object(_actions, "settings", self._settings_no_confluence()):
            assert _actions._is_confluence_postmortem_link(url) is False

    def test_configured_base_url_match(self):
        url = "https://mycompany.example.com/confluence/spaces/OPS/pages/1"
        s = self._settings_with_confluence_url("https://mycompany.example.com/confluence")
        with patch.object(_actions, "settings", s):
            assert _actions._is_confluence_postmortem_link(url) is True

    def test_configured_base_url_no_match(self):
        url = "https://other.example.com/page"
        s = self._settings_with_confluence_url("https://mycompany.example.com/confluence")
        with patch.object(_actions, "settings", s):
            assert _actions._is_confluence_postmortem_link(url) is False

    def test_plain_http_link_with_wiki_and_atlassian(self):
        url = "https://org.atlassian.net/wiki/spaces/TEAM/pages/9999"
        with patch.object(_actions, "settings", self._settings_no_confluence()):
            assert _actions._is_confluence_postmortem_link(url) is True


# ---------------------------------------------------------------------------
# _extract_confluence_page_id
# ---------------------------------------------------------------------------

class TestExtractConfluencePageId:
    def test_extracts_from_pages_path(self):
        url = "https://org.atlassian.net/wiki/spaces/OPS/pages/12345/Title"
        assert _actions._extract_confluence_page_id(url) == "12345"

    def test_extracts_from_page_id_query_param(self):
        url = "https://org.atlassian.net/wiki/display/OPS/Title?pageId=67890"
        assert _actions._extract_confluence_page_id(url) == "67890"

    def test_returns_none_when_no_match(self):
        url = "https://gitlab.example.com/group/-/issues/42"
        assert _actions._extract_confluence_page_id(url) is None

    def test_prefers_pages_path_over_query_param(self):
        url = "https://org.atlassian.net/wiki/spaces/OPS/pages/11111/Title?pageId=22222"
        # First pattern (/pages/\d+) matches before pageId=
        result = _actions._extract_confluence_page_id(url)
        assert result == "11111"

    def test_handles_bare_page_id_param(self):
        url = "https://org.atlassian.net/wiki/display/Space/Page?pageId=99999&src=search"
        assert _actions._extract_confluence_page_id(url) == "99999"


# ---------------------------------------------------------------------------
# _message_has_pin_marker
# ---------------------------------------------------------------------------

class TestMessageHasPinMarker:
    def _settings(self, reacji="pushpin"):
        return _make_settings(pin_content_reacji=reacji)

    def test_pinned_to_field_marks_message(self):
        message = {"pinned_to": ["C123"], "reactions": []}
        with patch.object(_actions, "settings", self._settings()):
            assert _actions._message_has_pin_marker(message) is True

    def test_matching_reaction_marks_message(self):
        message = {"reactions": [{"name": "pushpin", "count": 1}]}
        with patch.object(_actions, "settings", self._settings("pushpin")):
            assert _actions._message_has_pin_marker(message) is True

    def test_non_matching_reaction_returns_false(self):
        message = {"reactions": [{"name": "thumbsup", "count": 1}]}
        with patch.object(_actions, "settings", self._settings("pushpin")):
            assert _actions._message_has_pin_marker(message) is False

    def test_no_pins_no_reactions_returns_false(self):
        message = {}
        with patch.object(_actions, "settings", self._settings()):
            assert _actions._message_has_pin_marker(message) is False

    def test_empty_reactions_list_returns_false(self):
        message = {"reactions": []}
        with patch.object(_actions, "settings", self._settings()):
            assert _actions._message_has_pin_marker(message) is False


# ---------------------------------------------------------------------------
# _is_postmortem_announcement_message
# ---------------------------------------------------------------------------

class TestIsPostmortemAnnouncementMessage:
    def test_detects_view_postmortem_action(self):
        message = {
            "blocks": [
                {
                    "type": "actions",
                    "elements": [
                        {"action_id": "view_postmortem", "type": "button"}
                    ],
                }
            ]
        }
        assert _actions._is_postmortem_announcement_message(message) is True

    def test_returns_false_when_no_view_postmortem(self):
        message = {
            "blocks": [
                {
                    "type": "actions",
                    "elements": [
                        {"action_id": "some_other_action", "type": "button"}
                    ],
                }
            ]
        }
        assert _actions._is_postmortem_announcement_message(message) is False

    def test_returns_false_for_empty_blocks(self):
        assert _actions._is_postmortem_announcement_message({"blocks": []}) is False

    def test_returns_false_for_no_blocks_key(self):
        assert _actions._is_postmortem_announcement_message({}) is False

    def test_returns_false_for_section_block(self):
        message = {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn", "text": "Hi"}}
            ]
        }
        assert _actions._is_postmortem_announcement_message(message) is False

    def test_detects_action_nested_among_other_blocks(self):
        message = {
            "blocks": [
                {"type": "header", "text": {"type": "plain_text", "text": "Postmortem"}},
                {
                    "type": "actions",
                    "elements": [
                        {"action_id": "view_postmortem", "type": "button"}
                    ],
                },
            ]
        }
        assert _actions._is_postmortem_announcement_message(message) is True
