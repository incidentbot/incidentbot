from incidentbot.logging import logger
from incidentbot.matrix.client import MatrixClient
from incidentbot.matrix.messages import MatrixMessages
from incidentbot.platform.base import PlatformAdapter
from typing import Any


class MatrixAdapter(PlatformAdapter):
    """PlatformAdapter implementation for Matrix (via matrix-nio)."""

    def __init__(self, matrix_settings):
        self._matrix = MatrixClient(
            homeserver=matrix_settings.homeserver,
            user_id=matrix_settings.user_id,
            access_token=matrix_settings.access_token,
            device_id=matrix_settings.device_id,
        )
        self._digest_room_id = matrix_settings.digest_room_id
        self._widget_base_url = matrix_settings.widget_base_url

    @property
    def client(self) -> MatrixClient:
        return self._matrix

    def create_room(self, name: str, topic: str = "", private: bool = False) -> dict:
        return self._matrix.create_room(name=name, topic=topic, private=private)

    def set_room_topic(self, room_id: str, topic: str) -> None:
        self._matrix.set_room_topic(room_id, topic)

    def send_text(self, room_id: str, text: str) -> str:
        return self._matrix.send_text(room_id, text)

    def pin_message(self, room_id: str, event_id: str) -> None:
        self._matrix.pin_message(room_id, event_id)

    def add_bookmark(self, room_id: str, title: str, url: str, emoji: str = "") -> None:
        # Matrix has no bookmark feature; post as a pinned message instead
        event_id = self._matrix.send_text(
            room_id,
            f"🔖 {title}: {url}",
            f'🔖 <b>{title}:</b> <a href="{url}">{url}</a>',
        )
        if event_id:
            self._matrix.pin_message(room_id, event_id)

    def invite_user(self, room_id: str, user_id: str) -> None:
        self._matrix.invite_user(room_id, user_id)

    def invite_users(self, room_id: str, user_ids: list[str]) -> None:
        for user_id in user_ids:
            self._matrix.invite_user(room_id, user_id)

    def make_room_admin(self, room_id: str, user_id: str) -> None:
        self._matrix.set_room_admin(room_id, user_id)

    def get_group_members_by_name(self, group_name: str) -> list[str]:
        logger.warning(
            "matrix does not support usergroups, cannot auto-invite group; configure individual user ids via matrix.auto_invite_users instead",
            group_name=group_name,
        )
        return []

    def get_user_display_name(self, user_id: str) -> str:
        return self._matrix.get_display_name(user_id)

    def room_url(self, room_id: str) -> str:
        return f"https://matrix.to/#/{room_id}"

    def post_incident_boilerplate(self, incident: Any) -> str:
        plain, html = MatrixMessages.boilerplate(incident)
        return self._matrix.send_text(incident.channel_id, plain, html)

    def post_welcome_message(self, room_id: str) -> None:
        plain, html = MatrixMessages.welcome(room_id)
        self._matrix.send_text(room_id, plain, html)

    def post_roles_panel(self, room_id: str, incident: Any, participants: list) -> str:
        # Roles panel is Slack-specific (uses in-place message updates).
        # Matrix support is not yet implemented.
        return ""

    def post_digest_notification(
        self,
        channel_id: str,
        has_private_channel: bool,
        incident_components: str,
        incident_description: str,
        incident_impact: str | None,
        incident_slug: str,
        initial_status: str,
        meeting_link: str | None,
        severity: str,
    ) -> str:
        plain, html = MatrixMessages.digest_notification(
            channel_id=channel_id,
            has_private_channel=has_private_channel,
            incident_components=incident_components,
            incident_description=incident_description,
            incident_impact=incident_impact,
            incident_slug=incident_slug,
            initial_status=initial_status,
            meeting_link=meeting_link,
            severity=severity,
        )
        return self._matrix.send_text(self._digest_room_id, plain, html)

    def post_jira_issue(
        self, room_id: str, key: str, summary: str, issue_type: str, link: str
    ) -> str:
        plain, html = MatrixMessages.jira_issue(key, summary, issue_type, link)
        return self._matrix.send_text(room_id, plain, html)

    def post_gitlab_incident(
        self, room_id: str, incident_id: int, summary: str, link: str
    ) -> str:
        plain, html = MatrixMessages.gitlab_incident(incident_id, summary, link)
        return self._matrix.send_text(room_id, plain, html)

    def post_statuspage_prompt(self, room_id: str) -> None:
        plain = (
            "Statuspage integration is active. "
            "Update your Statuspage incident at the configured Statuspage URL."
        )
        self._matrix.send_text(room_id, plain)

    def post_phare_prompt(self, room_id: str) -> None:
        self._matrix.send_text(
            room_id,
            "Phare integration is active. Update your Phare incident at the configured Phare URL.",
        )
