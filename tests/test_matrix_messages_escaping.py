"""
Matrix messages are sent as formatted HTML, so every interpolated value has to be
escaped. Incident descriptions and components are free text typed by humans, so
an unescaped `<` or `&` silently breaks or swallows the rest of the message.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

_HOSTILE = 'A & B <script>alert("x")</script>'
_ESCAPED = "A &amp; B &lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"


@pytest.fixture(scope="module")
def messages():
    with patch("slack_sdk.WebClient", return_value=MagicMock()):
        from incidentbot.matrix.messages import MatrixMessages

    return MatrixMessages


def _incident():
    return SimpleNamespace(
        slug="inc-test",
        description=_HOSTILE,
        severity="sev1",
        status="investigating",
        components=_HOSTILE,
        impact=_HOSTILE,
        meeting_link="https://example.com/meet?a=1&b=2",
        channel_id="!room:example.com",
    )


def test_boilerplate_escapes_free_text(messages):
    _, html = messages.boilerplate(_incident())

    assert _ESCAPED in html
    assert "<script>" not in html
    assert "?a=1&amp;b=2" in html


def test_digest_notification_escapes_free_text(messages):
    _, html = messages.digest_notification(
        channel_id="!room:example.com",
        has_private_channel=False,
        incident_components=_HOSTILE,
        incident_description=_HOSTILE,
        incident_impact=_HOSTILE,
        incident_slug="inc-test",
        initial_status="investigating",
        meeting_link="https://example.com/meet?a=1&b=2",
        severity="sev1",
    )

    assert _ESCAPED in html
    assert "<script>" not in html


def test_plain_text_body_is_not_escaped(messages):
    """The plain body is the non-HTML fallback, escaping it would show entities."""
    plain, _ = messages.boilerplate(_incident())

    assert _HOSTILE in plain
    assert "&amp;" not in plain


@pytest.mark.parametrize(
    "builder,kwargs",
    [
        ("jira_issue", {"key": _HOSTILE, "summary": _HOSTILE, "issue_type": "Bug", "link": "https://example.com/a?b=1&c=2"}),
        ("gitlab_incident", {"incident_id": 1, "summary": _HOSTILE, "link": "https://example.com/a?b=1&c=2"}),
    ],
)
def test_integration_builders_escape_summaries(messages, builder, kwargs):
    _, html = getattr(messages, builder)(**kwargs)

    assert "<script>" not in html
    assert "?b=1&amp;c=2" in html


def test_reminder_escapes_message(messages):
    _, html = messages.reminder(SimpleNamespace(message=_HOSTILE), "inc-test")

    assert _ESCAPED in html
    assert "<script>" not in html
