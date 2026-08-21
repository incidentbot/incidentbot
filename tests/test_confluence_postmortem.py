from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from tests.runtime import load_module


postmortem_module = load_module(
    "incidentbot.confluence.postmortem",
    integrations=SimpleNamespace(
        atlassian=SimpleNamespace(
            confluence=SimpleNamespace(parent="Postmortems", space="OPS", template_id=1)
        )
    ),
)


def _build_image_event(*, title: str, message_ts: str, event_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=event_id,
        image=b"image-bytes",
        message_ts=message_ts,
        mimetype="image/png",
        title=title,
        created_at="2026-03-09 20:51:35",
        text=None,
    )


def _build_postmortem(timeline: list[SimpleNamespace]):
    exec_mock = MagicMock()
    confluence_api_mock = SimpleNamespace(api=exec_mock)

    with patch.object(
        postmortem_module,
        "ConfluenceApi",
        return_value=confluence_api_mock,
    ):
        postmortem = postmortem_module.IncidentPostmortem(
            incident=SimpleNamespace(created_at=datetime.now(timezone.utc)),
            participants=[],
            timeline=timeline,
            title="Incident Postmortem",
        )

    return postmortem, exec_mock


def test_generate_timeline_uses_stable_unique_attachment_names_for_duplicate_titles():
    item_one = _build_image_event(
        title="image.png",
        message_ts="1700000000.000100",
        event_id="event-1",
    )
    item_two = _build_image_event(
        title="image.png",
        message_ts="1700000000.000200",
        event_id="event-2",
    )
    postmortem, exec_mock = _build_postmortem([item_one, item_two])
    exec_mock.get_attachments_from_content.return_value = {"results": []}

    html = postmortem._IncidentPostmortem__generate_timeline("4010311692")

    assert exec_mock.attach_content.call_count == 2
    names = [call.kwargs["name"] for call in exec_mock.attach_content.call_args_list]
    assert names[0] != names[1]
    assert names[0].endswith(".png")
    assert names[1].endswith(".png")
    assert f'ri:filename="{names[0]}"' in html
    assert f'ri:filename="{names[1]}"' in html


def test_generate_timeline_skips_upload_when_attachment_already_exists():
    item = _build_image_event(
        title="image.png",
        message_ts="1700000000.000300",
        event_id="event-3",
    )
    postmortem, exec_mock = _build_postmortem([item])
    expected_name = postmortem._IncidentPostmortem__build_image_attachment_name(item)
    exec_mock.get_attachments_from_content.return_value = {
        "results": [{"title": expected_name}]
    }

    html = postmortem._IncidentPostmortem__generate_timeline("4010311692")

    exec_mock.attach_content.assert_not_called()
    assert f'ri:filename="{expected_name}"' in html


def test_generate_timeline_uses_legacy_attachment_name_when_present():
    item = _build_image_event(
        title="Image from iOS.jpg",
        message_ts="1700000000.000400",
        event_id="event-4",
    )
    postmortem, exec_mock = _build_postmortem([item])
    exec_mock.get_attachments_from_content.return_value = {
        "results": [{"title": "Image from iOS.jpg"}]
    }

    html = postmortem._IncidentPostmortem__generate_timeline("4010311692")

    exec_mock.attach_content.assert_not_called()
    assert 'ri:filename="Image from iOS.jpg"' in html
