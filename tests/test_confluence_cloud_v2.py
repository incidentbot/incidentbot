from datetime import datetime
from types import SimpleNamespace

import pytest

from incidentbot.confluence import api as confluence_api
from incidentbot.confluence import postmortem as postmortem_module


@pytest.fixture
def cloud(monkeypatch, requests_mock):
    settings = SimpleNamespace(
        ATLASSIAN_API_URL="https://example.atlassian.net",
        ATLASSIAN_API_USERNAME="bot@example.com",
        ATLASSIAN_API_TOKEN="test-token",
        integrations=SimpleNamespace(atlassian=SimpleNamespace(confluence=SimpleNamespace(
            space="PE", parent="Incidents", template_id=123,
        ))),
    )
    monkeypatch.setattr(confluence_api, "settings", settings)
    monkeypatch.setattr(postmortem_module, "settings", settings)
    base = f"{settings.ATLASSIAN_API_URL}/wiki"
    requests_mock.get(f"{base}/rest/api/content", status_code=410, json={"message": "This deprecated endpoint has been removed."})
    requests_mock.get(f"{base}/api/v2/spaces?keys=PE", json={"results": [{"id": "100", "key": "PE"}]})
    requests_mock.get(f"{base}/api/v2/pages?space-id=100&title=Incidents&status=current", json={"results": [{"id": "200"}]})
    return base

def test_startup_uses_supported_page_endpoint(cloud, requests_mock):
    assert confluence_api.ConfluenceApi().test() is True
    assert requests_mock.last_request.headers["Authorization"].startswith("Basic ")


@pytest.mark.parametrize("missing", ["space", "parent"])
def test_missing_parent_fails_startup(cloud, requests_mock, missing):
    path = "spaces" if missing == "space" else "pages"
    requests_mock.get(f"{cloud}/api/v2/{path}", json={"results": []})
    assert confluence_api.ConfluenceApi().test() is False


def test_permission_error_fails_startup(cloud, requests_mock):
    requests_mock.get(f"{cloud}/api/v2/spaces", status_code=403, json={"message": "Forbidden"})
    assert not confluence_api.ConfluenceApi().test()


@pytest.mark.parametrize("webui", ["/spaces/PE/pages/300", "/wiki/spaces/PE/pages/300"])
def test_postmortem_creates_updates_and_uploads_without_removed_endpoints(cloud, requests_mock, webui):
    requests_mock.get(f"{cloud}/rest/api/template/123", json={
        "name": "Incident", "body": {"storage": {"value": "<p>!ib-inject-description</p>!ib-inject-timeline"}},
    })
    requests_mock.get(f"{cloud}/api/v2/pages/200", json={"id": "200", "spaceId": "100"})
    created = requests_mock.post(f"{cloud}/api/v2/pages", json={"id": "300", "_links": {"webui": webui}})
    requests_mock.get(f"{cloud}/api/v2/pages/300?body-format=storage", json={
        "id": "300", "title": "Incident log", "version": {"number": 4},
        "body": {"storage": {"value": "<p>Review incident</p>!ib-inject-timeline"}},
    })
    attachment = requests_mock.put(f"{cloud}/rest/api/content/300/child/attachment", json={"results": [{"id": "400"}]})
    updated = requests_mock.put(f"{cloud}/api/v2/pages/300", json={"id": "300"})
    now = datetime(2026, 11, 10)
    incident = SimpleNamespace(created_at=now, updated_at=now, description="Review incident", impact="None", components="Test", severity="sev5")
    timeline = [SimpleNamespace(image=b"image-data", title="chart.png", mimetype="image/png", created_at=now)]
    postmortem = postmortem_module.IncidentPostmortem(incident, [], timeline, "Incident log")

    assert postmortem.create() == "https://example.atlassian.net/wiki/spaces/PE/pages/300"
    assert created.last_request.json() == {
        "spaceId": "100", "parentId": "200", "status": "current", "title": "Incident log",
        "body": {"representation": "storage", "value": "<p>Review incident</p>!ib-inject-timeline"},
    }
    payload = updated.last_request.json()
    assert payload["version"] == {"number": 5}
    assert payload["id"] == "300"
    assert payload["title"] == "Incident log"
    assert payload["body"]["representation"] == "storage"
    assert "!ib-inject-timeline" not in payload["body"]["value"]
    assert 'ri:filename="chart.png"' in payload["body"]["value"]
    assert attachment.called
    assert attachment.last_request.headers["X-Atlassian-Token"] == "nocheck"
    assert b"image-data" in attachment.last_request.body
