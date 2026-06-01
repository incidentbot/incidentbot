from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from incidentbot.slack.postmortem_sync_guard import reset_postmortem_sync_guard
from tests.runtime import load_module


handler = load_module("incidentbot.slack.handler")


def _sync_action_body() -> dict:
    return {
        "type": "block_actions",
        "container": {},
        "actions": [{"action_id": "incident.sync_postmortem"}],
        "channel": {"id": "C123"},
        "user": {"id": "U123"},
    }


@pytest.fixture(autouse=True)
def _reset_sync_guard_state():
    reset_postmortem_sync_guard()
    yield
    reset_postmortem_sync_guard()


def test_sync_postmortem_sends_started_ephemeral_and_runs_sync():
    ack = MagicMock()
    body = _sync_action_body()

    with (
        patch.object(
            handler,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(handler.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        handler.handle_sync_postmortem(ack, body)

    ack.assert_called_once()
    sync.assert_awaited_once_with(channel_id="C123")
    ephemeral.assert_called_once()
    assert "sync has started" in ephemeral.call_args.kwargs["text"].lower()


def test_sync_postmortem_noops_when_sync_is_already_in_progress():
    ack = MagicMock()
    body = _sync_action_body()

    with (
        patch.object(handler, "begin_postmortem_sync", return_value=False),
        patch.object(
            handler,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(handler.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        handler.handle_sync_postmortem(ack, body)

    ack.assert_called_once()
    sync.assert_not_awaited()
    ephemeral.assert_called_once()
    assert "already in progress" in ephemeral.call_args.kwargs["text"].lower()
