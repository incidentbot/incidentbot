from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from incidentbot.slack.postmortem_sync_guard import reset_postmortem_sync_guard
from tests.runtime import load_module


command = load_module("incidentbot.slack.command")


def _action_ids(blocks: list[dict]) -> list[str]:
    ids: list[str] = []
    for block in blocks:
        if block.get("type") != "actions":
            continue
        for element in block.get("elements", []):
            action_id = element.get("action_id")
            if isinstance(action_id, str):
                ids.append(action_id)
    return ids


def _postmortem_action_body() -> dict:
    return {
        "type": "block_actions",
        "container": {},
        "actions": [{"action_id": "incident.sync_or_create_postmortem"}],
        "channel": {"id": "C123"},
        "user": {"id": "U123"},
    }


def _assert_ephemeral_has_postmortem_link(ephemeral_mock, expected_link: str):
    kwargs = ephemeral_mock.call_args.kwargs
    assert kwargs.get("text")
    blocks = kwargs.get("blocks")
    assert isinstance(blocks, list) and len(blocks) == 2
    assert blocks[1]["elements"][0]["url"] == expected_link
    assert blocks[1]["elements"][0]["action_id"] == "view_postmortem"


def _assert_sync_started_message(ephemeral_mock):
    started_call = ephemeral_mock.call_args_list[0]
    assert "sync has started" in started_call.kwargs["text"].lower()
    assert "blocks" not in started_call.kwargs


@pytest.fixture(autouse=True)
def _reset_sync_guard_state():
    reset_postmortem_sync_guard()
    yield
    reset_postmortem_sync_guard()


def test_this_command_includes_sync_or_create_postmortem_button():
    with patch.object(command.settings, "roles", {"incident_coordinator": {}}):
        blocks = command.command_blocks(this=True)
    ids = _action_ids(blocks)

    assert "incident.sync_or_create_postmortem" in ids


def test_sync_or_create_postmortem_generates_and_syncs_for_confluence():
    ack = MagicMock()
    body = _postmortem_action_body()

    with (
        patch.object(
            command,
            "generate_postmortem",
            new=AsyncMock(
                return_value="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM"
            ),
        ) as generate,
        patch.object(
            command,
            "_is_confluence_postmortem_link",
            return_value=True,
        ),
        patch.object(
            command,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(command.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        command.handle_sync_or_create_postmortem(ack, body)

    ack.assert_called_once()
    generate.assert_awaited_once_with(channel_id="C123")
    sync.assert_awaited_once_with(channel_id="C123")
    assert ephemeral.call_count == 2
    _assert_sync_started_message(ephemeral)
    _assert_ephemeral_has_postmortem_link(
        ephemeral,
        "https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM",
    )


def test_sync_or_create_postmortem_generates_only_for_non_confluence():
    ack = MagicMock()
    body = _postmortem_action_body()

    with (
        patch.object(
            command,
            "generate_postmortem",
            new=AsyncMock(return_value="https://gitlab.example.com/group/-/issues/1"),
        ) as generate,
        patch.object(
            command,
            "_is_confluence_postmortem_link",
            return_value=False,
        ),
        patch.object(
            command,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(command.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        command.handle_sync_or_create_postmortem(ack, body)

    ack.assert_called_once()
    generate.assert_awaited_once_with(channel_id="C123")
    sync.assert_not_awaited()
    assert ephemeral.call_count == 2
    _assert_sync_started_message(ephemeral)
    _assert_ephemeral_has_postmortem_link(
        ephemeral,
        "https://gitlab.example.com/group/-/issues/1",
    )


def test_sync_or_create_postmortem_reports_when_generation_unavailable():
    ack = MagicMock()
    body = _postmortem_action_body()

    with (
        patch.object(
            command,
            "generate_postmortem",
            new=AsyncMock(return_value=None),
        ) as generate,
        patch.object(
            command,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(command.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        command.handle_sync_or_create_postmortem(ack, body)

    ack.assert_called_once()
    generate.assert_awaited_once_with(channel_id="C123")
    sync.assert_not_awaited()
    assert ephemeral.call_count == 2
    _assert_sync_started_message(ephemeral)
    assert "blocks" not in ephemeral.call_args.kwargs


def test_sync_or_create_postmortem_noops_when_another_sync_is_active():
    ack = MagicMock()
    body = _postmortem_action_body()

    with (
        patch.object(command, "begin_postmortem_sync", return_value=False),
        patch.object(
            command,
            "generate_postmortem",
            new=AsyncMock(
                return_value="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM"
            ),
        ) as generate,
        patch.object(
            command,
            "sync_postmortem",
            new=AsyncMock(return_value=True),
        ) as sync,
        patch.object(command.slack_web_client, "chat_postEphemeral") as ephemeral,
    ):
        command.handle_sync_or_create_postmortem(ack, body)

    ack.assert_called_once()
    generate.assert_not_awaited()
    sync.assert_not_awaited()
    ephemeral.assert_called_once()
    assert "already in progress" in ephemeral.call_args.kwargs["text"].lower()
