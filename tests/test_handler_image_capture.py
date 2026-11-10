from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from incidentbot.incident import actions
from tests.runtime import load_module


handler = load_module("incidentbot.slack.handler")


@pytest.fixture()
def capture():
    client = MagicMock()
    record = MagicMock()
    say = MagicMock()
    incident = SimpleNamespace(id=1, slug="inc-1")
    settings = SimpleNamespace(
        pin_content_reacji="pushpin", enable_pinned_images=True,
        options=SimpleNamespace(channel_name_prefix="inc"),
        SLACK_BOT_TOKEN="test-token", SLACK_USER_TOKEN="test-user-token",
    )
    with (
        patch.object(handler, "settings", settings),
        patch.object(actions, "settings", settings),
        patch.object(handler, "slack_web_client", client),
        patch.object(actions, "slack_web_client", client),
        patch.object(handler, "_download_pinned_image", actions._download_pinned_image, create=True),
        patch.object(handler.IncidentDatabaseInterface, "get_one", return_value=incident),
        patch.object(handler, "get_slack_user", return_value={"real_name": "Responder"}),
        patch.object(actions, "get_slack_user", return_value={"real_name": "Responder"}),
        patch.object(handler.EventLogHandler, "create", record),
        patch.object(actions.EventLogHandler, "create", record),
    ):
        yield SimpleNamespace(client=client, record=record, say=say, incident=incident)


def image(name="review.png", already_public=False):
    return {
        "id": f"F-{name}", "mimetype": "image/png", "name": name,
        "public_url_shared": already_public,
        "permalink_public": "https://slack-files.com/T123-F123-secret",
        "url_private": f"https://files.slack.com/files-pri/T1-F123/{name}",
    }


@pytest.mark.parametrize("already_public", [False, True])
@pytest.mark.parametrize("failure", [None, requests.HTTPError("denied"), requests.Timeout("timed out")])
def test_downloader_preserves_file_visibility(capture, already_public, failure):
    response = MagicMock(content=b"image bytes")
    if isinstance(failure, requests.HTTPError):
        response.raise_for_status.side_effect = failure
    with patch.object(actions.requests, "get", return_value=response) as download:
        if isinstance(failure, requests.Timeout):
            download.side_effect = failure
        content = actions._download_pinned_image(image(already_public=already_public))

    assert content == (None if failure else b"image bytes")
    download.assert_called_once_with(
        "https://files.slack.com/files-pri/T1-F123/review.png",
        headers={"Authorization": "Bearer test-token"}, timeout=(5, 30),
    )
    capture.client.files_sharedPublicURL.assert_not_called()
    capture.client.files_revokePublicURL.assert_not_called()


@pytest.mark.parametrize("path", ["reaction", "sync"])
@pytest.mark.parametrize("failure", [requests.HTTPError("denied"), requests.Timeout("timed out")])
def test_failed_image_does_not_skip_later_attachment(capture, path, failure):
    first = MagicMock()
    first.raise_for_status.side_effect = failure
    second = MagicMock(content=b"second image")
    message = {"ts": "1.0", "user": "U123", "files": [image("first.png"), image("second.png")]}
    capture.client.conversations_info.return_value = {"channel": {"name": "inc-1-review"}}
    capture.client.conversations_history.return_value = {"messages": [message]}
    with patch.object(actions.requests, "get", side_effect=[
        failure if isinstance(failure, requests.Timeout) else first, second,
    ]) as download:
        if path == "reaction":
            handler.reaction_added(
                {"reaction": "pushpin", "item": {"channel": "C123", "ts": "1.0"}}, capture.say,
            )
            capture.say.assert_called_once()
            assert "first.png" in capture.say.call_args.kwargs["text"]
            capture.client.reactions_add.assert_called_once()
        else:
            assert actions._upsert_pinned_message_event(capture.incident, message, set()) == 1

    assert download.call_count == 2
    capture.record.assert_called_once()
    assert capture.record.call_args.kwargs["image"] == b"second image"
    assert capture.record.call_args.kwargs["title"] == "second.png"
    capture.client.files_sharedPublicURL.assert_not_called()
    capture.client.files_revokePublicURL.assert_not_called()
