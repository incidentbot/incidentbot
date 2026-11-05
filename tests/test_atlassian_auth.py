import json
from types import SimpleNamespace
from urllib.parse import parse_qs
from uuid import UUID

import pytest
import requests
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
        ATLASSIAN_CLIENT_ID=None,
        ATLASSIAN_CLIENT_SECRET=None,
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


@pytest.mark.parametrize("webui", ["/spaces/ENG/pages/456", "/wiki/spaces/ENG/pages/456"])
def test_postmortem_browser_link_uses_site_url(atlassian_settings, monkeypatch, webui):
    from datetime import datetime
    from unittest.mock import MagicMock
    from incidentbot.confluence import postmortem

    api = MagicMock()
    api.fetch_template.return_value = SimpleNamespace(body="<p>Incident log</p>")
    api.api.get_page_by_id.return_value = {
        "title": "Incident log", "body": {"storage": {"value": "<p>Incident log</p>"}},
        "_links": {"base": f"https://api.atlassian.com/ex/confluence/{CLOUD_ID}/wiki", "webui": webui},
    }
    atlassian_settings.integrations = SimpleNamespace(atlassian=SimpleNamespace(confluence=SimpleNamespace(
        parent="Incidents", space="ENG", template_id=123,
    )))
    monkeypatch.setattr(postmortem, "settings", atlassian_settings)
    monkeypatch.setattr(postmortem, "ConfluenceApi", lambda: api)
    incident = SimpleNamespace(
        created_at=datetime(2026, 11, 10), updated_at=datetime(2026, 11, 10),
        description="Review incident", impact="None", components="Test", severity="sev5",
    )
    assert postmortem.IncidentPostmortem(incident, [], [], "Incident log").create() == (
        SITE_URL + "/wiki/spaces/ENG/pages/456"
    )


@pytest.fixture
def oauth_settings(monkeypatch):
    from incidentbot.atlassian_auth import _oauth_auth

    config = SimpleNamespace(
        ATLASSIAN_API_URL=SITE_URL,
        ATLASSIAN_CLOUD_ID=UUID(CLOUD_ID),
        ATLASSIAN_API_USERNAME=None,
        ATLASSIAN_API_TOKEN=None,
        ATLASSIAN_CLIENT_ID="test-client",
        ATLASSIAN_CLIENT_SECRET="test-secret",
    )
    monkeypatch.setattr(jira_api, "settings", config)
    monkeypatch.setattr(confluence_api, "settings", config)
    _oauth_auth.cache_clear()
    yield config
    _oauth_auth.cache_clear()


def test_oauth_is_shared_and_renews_before_expiry(oauth_settings, requests_mock, monkeypatch):
    from incidentbot import atlassian_auth

    oauth_settings.ATLASSIAN_API_USERNAME = "old@example.com"
    oauth_settings.ATLASSIAN_API_TOKEN = "old-token"
    monkeypatch.setattr(atlassian_auth, "monotonic", lambda: 100)
    tokens = requests_mock.post(
        "https://auth.atlassian.com/oauth/token",
        [
            {"json": {"access_token": "first-token", "token_type": "Bearer", "expires_in": 3600}},
            {"json": {"access_token": "second-token", "token_type": "Bearer", "expires_in": 3600}},
            {"status_code": 401},
        ],
    )
    jira_request = requests_mock.get(
        f"https://api.atlassian.com/ex/jira/{CLOUD_ID}/rest/api/2/project/INF",
        json={"id": "10000"},
    )
    confluence_request = requests_mock.get(
        f"https://api.atlassian.com/ex/confluence/{CLOUD_ID}/wiki/rest/api/template/123",
        json={"name": "Postmortem", "body": {"storage": {"value": "<p>Template</p>"}}},
    )
    jira = jira_api.JiraApi()
    jira.api.get_project("INF")
    assert confluence_api.ConfluenceApi().fetch_template(123).name == "Postmortem"
    assert tokens.call_count == 1
    assert jira_request.last_request.headers["Authorization"] == "Bearer first-token"
    assert confluence_request.last_request.headers["Authorization"] == "Bearer first-token"
    assert parse_qs(tokens.last_request.text) == {
        "grant_type": ["client_credentials"],
        "client_id": ["test-client"],
        "client_secret": ["test-secret"],
    }

    monkeypatch.setattr(atlassian_auth, "monotonic", lambda: 3671)
    jira.api.get_project("INF")
    assert tokens.call_count == 2
    assert jira_request.last_request.headers["Authorization"] == "Bearer second-token"

    monkeypatch.setattr(atlassian_auth, "monotonic", lambda: 7242)
    with pytest.raises(RuntimeError, match="HTTP 401"):
        jira.api.get_project("INF")
    assert jira_request.call_count == 2


@pytest.mark.parametrize("response", [
    {"status_code": 401, "json": {"error_description": "test-secret"}},
    {"status_code": 302, "headers": {"Location": "https://other.example/token"}},
    {"text": "not-json"},
    {"json": []},
    {"exc": requests.Timeout("test-secret")},
    {"json": {"access_token": "", "token_type": "Bearer", "expires_in": 3600}},
    {"json": {"access_token": "test-token", "token_type": "Basic", "expires_in": 3600}},
    {"json": {"access_token": "test-token", "token_type": None, "expires_in": 3600}},
    {"json": {"access_token": "test-token", "token_type": "Bearer", "expires_in": 0}},
    {"json": {"access_token": "test-token", "token_type": "Bearer", "expires_in": "invalid"}},
    {"json": {"access_token": "test-token", "token_type": "Bearer", "expires_in": True}},
])
def test_oauth_fails_closed(oauth_settings, requests_mock, response):
    requests_mock.post("https://auth.atlassian.com/oauth/token", **response)
    with pytest.raises(RuntimeError) as error:
        jira_api.JiraApi().api.get_project("INF")
    assert "test-secret" not in str(error.value)
    assert requests_mock.call_count == 1


@pytest.mark.parametrize("url", ["https://other.example", "http://api.atlassian.com"])
def test_oauth_does_not_send_credentials_outside_https_gateway(oauth_settings, requests_mock, url):
    from incidentbot.atlassian_auth import client_auth

    session = client_auth(oauth_settings)["session"]
    with pytest.raises(ValueError, match="API gateway"):
        session.get(url)
    assert requests_mock.call_count == 0


@pytest.mark.parametrize("missing", [None, "ATLASSIAN_CLOUD_ID", "ATLASSIAN_CLIENT_ID", "ATLASSIAN_CLIENT_SECRET"])
def test_oauth_configuration_validation(monkeypatch, missing):
    monkeypatch.setenv("IS_TEST_ENVIRONMENT", "false")
    for name in ["SLACK_APP_TOKEN", "SLACK_BOT_TOKEN", "SLACK_USER_TOKEN"]:
        monkeypatch.setenv(name, "test-token")
    for name, value in {
        "ATLASSIAN_API_URL": SITE_URL,
        "ATLASSIAN_CLOUD_ID": CLOUD_ID,
        "ATLASSIAN_CLIENT_ID": "test-client",
        "ATLASSIAN_CLIENT_SECRET": "test-secret",
    }.items():
        monkeypatch.setenv(name, "" if name == missing else value)
    monkeypatch.setenv("ATLASSIAN_API_USERNAME", "")
    monkeypatch.setenv("ATLASSIAN_API_TOKEN", "")
    monkeypatch.setenv("INTEGRATIONS", json.dumps({"atlassian": {
        "jira": {"enabled": True, "issue_types": ["Task"], "project": "INF", "status_mapping": []},
        "confluence": {"enabled": True, "parent": "Incidents", "space": "PE", "template_id": 123},
    }}))

    if missing:
        with pytest.raises(ValidationError, match=missing) as error:
            Settings()
        assert "test-secret" not in str(error.value)
    else:
        config = Settings()
        expected_cloud_id = UUID(CLOUD_ID)
        assert expected_cloud_id == config.ATLASSIAN_CLOUD_ID
