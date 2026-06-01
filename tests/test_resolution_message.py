from types import SimpleNamespace

from tests.runtime import load_module


messages = load_module(
    "incidentbot.slack.messages",
    statuses={
        "investigating": SimpleNamespace(final=False),
        "resolved": SimpleNamespace(final=True),
    },
    icons={"slack": {"postmortem": ":book:"}},
    links=None,
)


def action_ids(message_blocks: list[dict]) -> list[str]:
    ids = []
    for block in message_blocks:
        if block.get("type") != "actions":
            continue
        for element in block.get("elements", []):
            if element.get("action_id"):
                ids.append(element.get("action_id"))
    return ids


def test_resolution_message_exposes_manual_generation():
    """When no postmortem exists and sync is unavailable, only Generate is shown."""
    message = messages.BlockBuilder.resolution_message(channel="C123")
    ids = action_ids(message["blocks"])

    assert "incident.generate_postmortem" in ids
    # Disabled/unavailable buttons are hidden entirely — not rendered
    assert "incident.sync_postmortem.disabled" not in ids
    assert "incident.sync_postmortem" not in ids
    assert "incident.generate_postmortem.disabled" not in ids


def test_resolution_message_with_sync_unavailable_hides_sync_button():
    """sync_pinned_content_enabled=False → Sync Pinned Content button is not shown at all."""
    message = messages.BlockBuilder.resolution_message(
        channel="C123",
        postmortem_link="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM",
        sync_pinned_content_enabled=False,
    )
    ids = action_ids(message["blocks"])

    assert "view_postmortem" in ids
    assert "incident.sync_postmortem" not in ids
    assert "incident.sync_postmortem.disabled" not in ids


def test_resolution_message_shows_existing_postmortem_state():
    """When postmortem exists and sync is available, View + Sync are shown; Generate is not."""
    message = messages.BlockBuilder.resolution_message(
        channel="C123",
        postmortem_link="https://example.atlassian.net/wiki/spaces/OPS/pages/12345/PM",
        sync_pinned_content_enabled=True,
    )
    ids = action_ids(message["blocks"])

    assert "view_postmortem" in ids
    assert "incident.sync_postmortem" in ids
    # Generate is replaced by View when a postmortem already exists
    assert "incident.generate_postmortem" not in ids
    assert "incident.generate_postmortem.disabled" not in ids
