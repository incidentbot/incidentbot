from types import SimpleNamespace
from uuid import UUID

import pytest
from pydantic import ValidationError

from incidentbot.configuration.settings import Settings
from incidentbot.confluence import api as confluence_api
from incidentbot.jira import api as jira_api


CLOUD_ID = "12345678-1234-5678-1234-567812345678"
SITE_URL = "https://example.atlassian.net"


@pytest.fixture(params=[None, CLOUD_ID], ids=["site", "gateway"])
def atlassian_settings(request, monkeypatch):
    settings = SimpleNamespace(
        ATLASSIAN_API_URL=SITE_URL,
        ATLASSIAN_CLOUD_ID=UUID(request.param) if request.param else None,
        ATLASSIAN_API_USERNAME="bot@example.com",
        ATLASSIAN_API_TOKEN="test-token",
    )
    monkeypatch.setattr(jira_api, "settings", settings)
    monkeypatch.setattr(confluence_api, "settings", settings)
    return settings


def test_jira_routes_requests(atlassian_settings, requests_mock):
    base = (
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}"
        if atlassian_settings.ATLASSIAN_CLOUD_ID
        else SITE_URL
    )
    requests_mock.get(f"{base}/rest/api/2/project/INF", json={"id": "10000"})

    assert jira_api.JiraApi().api.get_project("INF") == {"id": "10000"}
    assert requests_mock.last_request.headers["Authorization"].startswith("Basic ")
    assert atlassian_settings.ATLASSIAN_API_URL == SITE_URL


def test_confluence_routes_templates_and_pages(atlassian_settings, requests_mock):
    base = (
        f"https://api.atlassian.com/ex/confluence/{CLOUD_ID}/wiki"
        if atlassian_settings.ATLASSIAN_CLOUD_ID
        else f"{SITE_URL}/wiki"
    )
    requests_mock.get(
        f"{base}/rest/api/template/123",
        json={"name": "Postmortem", "body": {"storage": {"value": "<p>Template</p>"}}},
    )
    requests_mock.get(
        f"{base}/rest/api/content", json={"results": [{"id": "456"}]}
    )

    client = confluence_api.ConfluenceApi()
    assert client.fetch_template(123).body == "<p>Template</p>"
    assert client.api.get_page_id("PE", "Incidents") == "456"
    assert client.api.page_exists("PE", "Incidents")
    assert requests_mock.last_request.headers["Authorization"].startswith("Basic ")


def test_cloud_id_is_validated(monkeypatch):
    monkeypatch.setenv("ATLASSIAN_CLOUD_ID", "not-a-cloud-id")
    with pytest.raises(ValidationError, match="ATLASSIAN_CLOUD_ID"):
        Settings()
