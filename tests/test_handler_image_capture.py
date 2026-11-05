from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
import requests

from tests.runtime import load_module


handler = load_module("incidentbot.slack.handler")


@pytest.mark.parametrize("already_public", [False, True])
@pytest.mark.parametrize("download_fails", [False, True])
def test_image_capture_preserves_file_visibility(already_public, download_fails):
    client = MagicMock()
    client.conversations_info.return_value = {"channel": {"name": "inc-1-review"}}
    client.conversations_history.return_value = {"messages": [{
        "ts": "1.0", "user": "U123", "files": [{
            "id": "F123", "mimetype": "image/png", "name": "review.png",
            "public_url_shared": already_public,
            "permalink_public": "https://slack-files.com/T123-F123-secret",
            "url_private": "https://files.slack.com/files-pri/T1-F123/review.png",
        }],
    }]}
    response = MagicMock(content=b"image bytes")
    if download_fails:
        response.raise_for_status.side_effect = requests.HTTPError("download denied")
    settings = SimpleNamespace(
        pin_content_reacji="pushpin", enable_pinned_images=True,
        options=SimpleNamespace(channel_name_prefix="inc"), SLACK_BOT_TOKEN="test-token",
    )
    with (
        patch.object(handler, "settings", settings),
        patch.object(handler, "slack_web_client", client),
        patch.object(handler.IncidentDatabaseInterface, "get_one", return_value=SimpleNamespace(id=1, slug="inc-1")),
        patch.object(handler, "get_slack_user", return_value={"real_name": "Responder"}),
        patch.object(handler.requests, "get", return_value=response) as download,
        patch.object(handler.EventLogHandler, "create") as record,
    ):
        handler.reaction_added({"reaction": "pushpin", "item": {"channel": "C123", "ts": "1.0"}}, MagicMock())

    download.assert_called_once_with(
        "https://files.slack.com/files-pri/T1-F123/review.png",
        headers={"Authorization": "Bearer test-token"}, timeout=(5, 30),
    )
    client.files_sharedPublicURL.assert_not_called()
    client.files_revokePublicURL.assert_not_called()
    if download_fails:
        record.assert_not_called()
        client.reactions_add.assert_not_called()
    else:
        assert record.call_args.kwargs["image"] == b"image bytes"
        client.reactions_add.assert_called_once()
