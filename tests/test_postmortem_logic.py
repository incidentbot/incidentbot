import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from tests.runtime import load_module


actions = load_module(
    "incidentbot.incident.actions",
    statuses={
        "investigating": SimpleNamespace(final=False),
        "resolved": SimpleNamespace(final=True),
        "closed": SimpleNamespace(final=True),
    },
)


def incident() -> SimpleNamespace:
    return SimpleNamespace(
        id=123,
        slug="incident-123",
        description="Database outage",
        channel_name="incident-123-database-outage",
        channel_id="C123",
    )


def test_is_final_status_accepts_any_final_status():
    assert actions._is_final_status("resolved")
    assert actions._is_final_status("closed")
    assert not actions._is_final_status("investigating")


def test_extract_confluence_page_id_from_supported_urls():
    direct_page_path = (
        "https://example.atlassian.net/wiki/spaces/OPS/pages/123456/My+Page"
    )
    query_page_path = (
        "https://example.atlassian.net/wiki/pages/viewpage.action?pageId=98765"
    )

    assert actions._extract_confluence_page_id(direct_page_path) == "123456"
    assert actions._extract_confluence_page_id(query_page_path) == "98765"
    assert actions._extract_confluence_page_id("https://example.com/no-page") is None


def test_is_confluence_postmortem_link_detects_cloud_urls():
    assert actions._is_confluence_postmortem_link(
        "https://myorg.atlassian.net/wiki/spaces/OPS/pages/12345/Doc"
    )
    assert not actions._is_confluence_postmortem_link(
        "https://gitlab.example.com/group/project/-/issues/1#note_1"
    )


def test_is_confluence_postmortem_link_uses_atlassian_api_url_fallback():
    integrations = SimpleNamespace(
        atlassian=SimpleNamespace(confluence=SimpleNamespace(enabled=True))
    )
    with (
        patch.object(actions.settings, "integrations", integrations),
        patch.object(
            actions.settings, "ATLASSIAN_API_URL", "https://confluence.internal"
        ),
    ):
        assert actions._is_confluence_postmortem_link(
            "https://confluence.internal/wiki/spaces/OPS/pages/12345/PM"
        )


def test_get_or_create_reuses_existing_postmortem():
    with (
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value="https://example.com/postmortem/1",
        ),
        patch.object(actions, "_create_new_postmortem") as create_new,
        patch.object(
            actions.IncidentDatabaseInterface, "add_postmortem"
        ) as add_postmortem,
        patch.object(actions.EventLogHandler, "create") as write_event,
        patch.object(actions, "_announce_postmortem") as announce,
    ):
        link = actions._get_or_create_postmortem_link(incident())

    assert link == "https://example.com/postmortem/1"
    create_new.assert_not_called()
    add_postmortem.assert_not_called()
    write_event.assert_not_called()
    announce.assert_not_called()


def test_get_or_create_creates_records_and_announces_once():
    inc = incident()

    with (
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value=None,
        ),
        patch.object(
            actions,
            "_create_new_postmortem",
            return_value="https://example.com/postmortem/2",
        ),
        patch.object(
            actions.IncidentDatabaseInterface, "add_postmortem"
        ) as add_postmortem,
        patch.object(actions.EventLogHandler, "create") as write_event,
        patch.object(actions, "_announce_postmortem") as announce,
    ):
        link = actions._get_or_create_postmortem_link(inc)

    assert link == "https://example.com/postmortem/2"
    add_postmortem.assert_called_once_with(
        parent=inc.id,
        url="https://example.com/postmortem/2",
    )
    assert write_event.call_count == 1
    announce.assert_called_once_with(inc, "https://example.com/postmortem/2")


def test_create_new_postmortem_falls_back_to_gitlab():
    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "list_participants",
            return_value=[],
        ),
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[],
        ),
        patch.object(
            actions,
            "_create_confluence_postmortem",
            return_value=None,
        ) as create_confluence,
        patch.object(
            actions,
            "_create_gitlab_postmortem",
            return_value="https://example.com/postmortem/gitlab",
        ) as create_gitlab,
    ):
        link = actions._create_new_postmortem(incident())

    assert link == "https://example.com/postmortem/gitlab"
    create_confluence.assert_called_once()
    create_gitlab.assert_called_once()


def test_create_new_postmortem_stops_after_first_success():
    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "list_participants",
            return_value=[],
        ),
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[],
        ),
        patch.object(
            actions,
            "_create_confluence_postmortem",
            return_value="https://example.com/postmortem/confluence",
        ) as create_confluence,
        patch.object(
            actions,
            "_create_gitlab_postmortem",
            return_value="https://example.com/postmortem/gitlab",
        ) as create_gitlab,
    ):
        link = actions._create_new_postmortem(incident())

    assert link == "https://example.com/postmortem/confluence"
    create_confluence.assert_called_once()
    create_gitlab.assert_not_called()


def test_generate_postmortem_requires_final_status():
    inc = incident()
    inc.status = "investigating"

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(actions.slack_web_client, "chat_postMessage") as chat_post,
    ):
        result = asyncio.run(actions.generate_postmortem(channel_id=inc.channel_id))

    assert result is None
    chat_post.assert_called_once()


def test_generate_postmortem_updates_digest_on_success():
    inc = incident()
    inc.status = "resolved"
    inc.has_private_channel = False
    inc.components = "api"
    inc.impact = "customer impact"
    inc.meeting_link = "https://zoom.example.com/abc"
    inc.severity = "sev1"
    inc.digest_message_ts = "12345.678"

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_backfill_pinned_content_from_channel",
            return_value={
                "messages_scanned": 0,
                "pin_candidates": 0,
                "events_created": 0,
            },
        ),
        patch.object(
            actions,
            "_get_or_create_postmortem_link",
            return_value="https://example.com/postmortem/123",
        ),
        patch.object(
            actions,
            "get_digest_channel_id",
            return_value="CDIGEST",
        ),
        patch.object(
            actions.IncidentChannelDigestNotification,
            "update",
            return_value=[],
        ),
        patch.object(actions.slack_web_client, "chat_update") as chat_update,
    ):
        result = asyncio.run(actions.generate_postmortem(channel_id=inc.channel_id))

    assert result == "https://example.com/postmortem/123"
    chat_update.assert_called_once()


def test_generate_postmortem_allows_closed_status():
    inc = incident()
    inc.status = "closed"
    inc.has_private_channel = False
    inc.components = "api"
    inc.impact = "customer impact"
    inc.meeting_link = "https://zoom.example.com/abc"
    inc.severity = "sev1"
    inc.digest_message_ts = "12345.678"

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_backfill_pinned_content_from_channel",
            return_value={
                "messages_scanned": 0,
                "pin_candidates": 0,
                "events_created": 0,
            },
        ),
        patch.object(
            actions,
            "_get_or_create_postmortem_link",
            return_value="https://example.com/postmortem/closed",
        ),
        patch.object(
            actions,
            "get_digest_channel_id",
            return_value="CDIGEST",
        ),
        patch.object(
            actions.IncidentChannelDigestNotification,
            "update",
            return_value=[],
        ),
        patch.object(actions.slack_web_client, "chat_update") as chat_update,
    ):
        result = asyncio.run(actions.generate_postmortem(channel_id=inc.channel_id))

    assert result == "https://example.com/postmortem/closed"
    chat_update.assert_called_once()


def test_sync_postmortem_requires_existing_link():
    inc = incident()

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value=None,
        ),
        patch.object(actions.slack_web_client, "chat_postMessage") as chat_post,
    ):
        result = asyncio.run(actions.sync_postmortem(channel_id=inc.channel_id))

    assert result is False
    chat_post.assert_called_once()


def test_sync_postmortem_rejects_non_confluence_links():
    inc = incident()
    integrations = SimpleNamespace(
        atlassian=SimpleNamespace(confluence=SimpleNamespace(enabled=True))
    )

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value="https://gitlab.example.com/group/project/-/issues/1#note_1",
        ),
        patch.object(actions.settings, "integrations", integrations),
        patch.object(actions.slack_web_client, "chat_postMessage") as chat_post,
    ):
        result = asyncio.run(actions.sync_postmortem(channel_id=inc.channel_id))

    assert result is False
    chat_post.assert_called_once()


def test_sync_postmortem_success_path():
    inc = incident()
    integrations = SimpleNamespace(
        atlassian=SimpleNamespace(confluence=SimpleNamespace(enabled=True))
    )

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM",
        ),
        patch.object(actions.settings, "integrations", integrations),
        patch.object(
            actions,
            "_backfill_pinned_content_from_channel",
            return_value={
                "messages_scanned": 10,
                "pin_candidates": 2,
                "events_created": 0,
            },
        ),
        patch.object(
            actions,
            "_sync_confluence_postmortem",
            return_value=True,
        ),
        patch.object(actions.EventLogHandler, "create") as write_event,
        patch.object(actions.slack_web_client, "chat_postMessage") as chat_post,
    ):
        result = asyncio.run(actions.sync_postmortem(channel_id=inc.channel_id))

    assert result is True
    assert write_event.call_count == 1
    chat_post.assert_called_once()


def test_sync_postmortem_backfills_pins_before_sync():
    inc = incident()
    integrations = SimpleNamespace(
        atlassian=SimpleNamespace(confluence=SimpleNamespace(enabled=True))
    )

    with (
        patch.object(
            actions.IncidentDatabaseInterface,
            "get_one",
            return_value=inc,
        ),
        patch.object(
            actions,
            "_get_existing_postmortem_link",
            return_value="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM",
        ),
        patch.object(actions.settings, "integrations", integrations),
        patch.object(
            actions,
            "_backfill_pinned_content_from_channel",
            return_value={
                "messages_scanned": 20,
                "pin_candidates": 3,
                "events_created": 2,
            },
        ) as backfill,
        patch.object(
            actions,
            "_sync_confluence_postmortem",
            return_value=True,
        ) as sync_pm,
        patch.object(actions.EventLogHandler, "create") as write_event,
        patch.object(actions.slack_web_client, "chat_postMessage") as chat_post,
    ):
        result = asyncio.run(actions.sync_postmortem(channel_id=inc.channel_id))

    assert result is True
    backfill.assert_called_once_with(inc)
    sync_pm.assert_called_once()
    assert write_event.call_count == 2
    assert "Backfilled 2 pinned item(s)" in chat_post.call_args.kwargs["text"]


def test_backfill_pinned_content_skips_existing_text_pin():
    inc = incident()
    existing_pin = SimpleNamespace(
        source="pin",
        image=None,
        message_ts="123.456",
        text="Existing pinned note",
        title=None,
        mimetype=None,
    )
    pin_message = {
        "ts": "123.456",
        "text": "hello",
        "reactions": [{"name": "pushpin"}],
    }

    with (
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[existing_pin],
        ),
        patch.object(
            actions,
            "_list_channel_messages",
            return_value=[pin_message],
        ),
        patch.object(
            actions,
            "_parse_pinned_message_content",
            return_value="Existing pinned note",
        ),
        patch.object(actions.EventLogHandler, "create") as write_event,
    ):
        result = actions._backfill_pinned_content_from_channel(inc)

    assert result["events_created"] == 0
    write_event.assert_not_called()


def test_backfill_pinned_content_creates_missing_text_pin():
    inc = incident()
    pin_message = {
        "ts": "123.456",
        "user": "U123",
        "text": "new",
        "reactions": [{"name": "pushpin"}],
    }

    with (
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[],
        ),
        patch.object(
            actions,
            "_list_channel_messages",
            return_value=[pin_message],
        ),
        patch.object(
            actions,
            "_parse_pinned_message_content",
            return_value="New pinned context",
        ),
        patch.object(
            actions,
            "_resolve_pinned_event_user",
            return_value="Person One",
        ),
        patch.object(actions.EventLogHandler, "create") as write_event,
    ):
        result = actions._backfill_pinned_content_from_channel(inc)

    assert result["events_created"] == 1
    write_event.assert_called_once()


def test_backfill_pinned_content_skips_postmortem_announcement_pin():
    inc = incident()
    postmortem_announcement = {
        "ts": "123.456",
        "text": "postmortem message",
        "reactions": [{"name": "pushpin"}],
        "blocks": [
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "action_id": "view_postmortem",
                    }
                ],
            }
        ],
    }

    with (
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[],
        ),
        patch.object(
            actions,
            "_list_channel_messages",
            return_value=[postmortem_announcement],
        ),
        patch.object(actions, "_upsert_pinned_message_event") as upsert_pin,
    ):
        result = actions._backfill_pinned_content_from_channel(inc)

    assert result["messages_scanned"] == 1
    assert result["pin_candidates"] == 0
    assert result["events_created"] == 0
    upsert_pin.assert_not_called()


def test_backfill_pinned_content_skips_existing_image_pin():
    inc = incident()
    existing_image_pin = SimpleNamespace(
        source="pin",
        image=b"image-bytes",
        message_ts="123.456",
        text=None,
        title="Screenshot.png",
        mimetype="image/png",
    )
    pin_message = {
        "ts": "123.456",
        "user": "U123",
        "reactions": [{"name": "pushpin"}],
        "files": [
            {
                "id": "F123",
                "name": "Screenshot.png",
                "mimetype": "image/png",
                "url_private": "https://files.example/screenshot.png",
            }
        ],
    }

    with (
        patch.object(
            actions.EventLogHandler,
            "read",
            return_value=[existing_image_pin],
        ),
        patch.object(
            actions,
            "_list_channel_messages",
            return_value=[pin_message],
        ),
        patch.object(actions, "_download_pinned_image") as download_image,
        patch.object(
            actions,
            "_resolve_pinned_event_user",
            return_value="Person One",
        ),
        patch.object(actions.EventLogHandler, "create") as write_event,
    ):
        result = actions._backfill_pinned_content_from_channel(inc)

    assert result["events_created"] == 0
    download_image.assert_not_called()
    write_event.assert_not_called()
