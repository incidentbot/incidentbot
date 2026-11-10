import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from incidentbot.zoom.meeting import ZoomMeeting
from tests.runtime import load_module


@pytest.mark.parametrize("failure", [
    requests.Timeout("token timed out"), requests.ConnectionError("offline"),
    requests.HTTPError("token denied"), ValueError("invalid JSON"),
    None, "", 123,
])
def test_token_failure_does_not_interrupt_incident_setup(failure):
    core = load_module("incidentbot.incident.core", integrations=SimpleNamespace(
        zoom=SimpleNamespace(enabled=True),
    ))
    response = MagicMock()
    response.json.return_value = {"access_token": failure}
    response.text = json.dumps({"access_token": failure if not isinstance(failure, Exception) else None})
    if isinstance(failure, requests.HTTPError):
        response.raise_for_status.side_effect = failure
    elif isinstance(failure, ValueError):
        response.json.side_effect = failure
    with patch("incidentbot.zoom.meeting.requests.post", return_value=response) as post:
        if isinstance(failure, requests.RequestException) and not isinstance(failure, requests.HTTPError):
            post.side_effect = failure
        assert core.Incident().generate_meeting_link("inc-review") is None
    assert post.call_count == 1
    assert post.call_args.kwargs["timeout"] == (5, 15)


@pytest.mark.parametrize("failure", [requests.Timeout("meeting timed out"), "denied", "invalid JSON"])
def test_meeting_failure_returns_no_link(failure):
    token = MagicMock()
    token.json.return_value = {"access_token": "test-token"}
    token.text = json.dumps({"access_token": "test-token"})
    meeting = MagicMock(status_code=400 if failure == "denied" else 201)
    if failure == "invalid JSON":
        meeting.json.side_effect = ValueError("invalid JSON")
    with patch("incidentbot.zoom.meeting.requests.post", side_effect=[
        token, failure if isinstance(failure, Exception) else meeting,
    ]) as post:
        assert ZoomMeeting("inc-review").url is None
    assert post.call_args.kwargs["timeout"] == (5, 15)


def test_server_to_server_meeting_creation_keeps_existing_endpoint():
    token = MagicMock()
    token.json.return_value = {"access_token": "test-token"}
    token.text = json.dumps({"access_token": "test-token"})
    meeting = MagicMock(status_code=201)
    meeting.json.return_value = {"join_url": "https://zoom.us/j/123"}
    meeting.text = json.dumps({"join_url": "https://zoom.us/j/123"})
    with patch("incidentbot.zoom.meeting.requests.post", side_effect=[token, meeting]) as post:
        assert ZoomMeeting("inc-review").url == "https://zoom.us/j/123"
    assert post.call_args_list[0].args[0] == "https://zoom.us/oauth/token"
    assert post.call_args_list[0].kwargs["params"]["grant_type"] == "account_credentials"
    assert post.call_args.args[0] == "https://api.zoom.us/v2/users/me/meetings"
    assert post.call_args.kwargs["headers"]["authorization"] == "Bearer test-token"
