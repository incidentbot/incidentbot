from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from incidentbot.confluence.postmortem import IncidentPostmortem


@pytest.mark.parametrize("elapsed, expected", [
    (timedelta(minutes=45), "0h45m"),
    (timedelta(hours=1, minutes=15), "1h15m"),
    (timedelta(days=1), "24h0m"),
    (timedelta(days=2, hours=1, minutes=15), "49h15m"),
])
def test_generated_postmortem_duration_includes_whole_days(elapsed, expected):
    now = datetime(2026, 11, 5, 12)
    incident = SimpleNamespace(
        created_at=now - elapsed, updated_at=now, description="Review incident",
        impact="No impact", components="Test", severity="sev5",
    )
    api = MagicMock()
    api.fetch_template.return_value = SimpleNamespace(body="<p>!ib-inject-duration</p>")
    api.api.get_page_by_id.side_effect = [
        {"_links": {"base": "https://example.atlassian.net", "webui": "/wiki/page"}},
        {"title": "Incident log", "body": {"storage": {"value": "<p>Timeline</p>"}}},
    ]
    with (
        patch("incidentbot.confluence.postmortem.settings") as settings,
        patch("incidentbot.confluence.postmortem.ConfluenceApi", return_value=api),
        patch("incidentbot.confluence.postmortem.datetime.datetime") as clock,
    ):
        settings.integrations.atlassian.confluence.parent = "Incidents"
        settings.integrations.atlassian.confluence.space = "PE"
        clock.now.return_value = now
        postmortem = IncidentPostmortem(incident, [], [], "Incident log")
        assert postmortem.create() == "https://example.atlassian.net/wiki/page"
    assert api.api.create_page.call_args.args[2] == f"<p>{expected}</p>"
