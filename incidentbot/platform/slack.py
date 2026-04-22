from incidentbot.configuration.settings import settings
from incidentbot.logging import logger
from incidentbot.platform.base import PlatformAdapter
from typing import Any


class SlackAdapter(PlatformAdapter):
    """Wraps the existing Slack SDK client into the PlatformAdapter interface."""

    def __init__(self):
        from incidentbot.slack.client import slack_web_client, slack_workspace_id, all_workspace_groups
        self._client = slack_web_client
        self._workspace_id = slack_workspace_id
        self._workspace_groups = all_workspace_groups

    def create_room(self, name: str, topic: str = "", private: bool = False) -> dict:
        import slack_sdk.errors
        logger.info(f"Creating Slack channel: {name}")
        try:
            resp = self._client.conversations_create(name=name, is_private=private)
            channel = resp.get("channel")
            return {"id": channel["id"], "name": channel["name"]}
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error creating channel {name}: {error}")
            return {}

    def set_room_topic(self, room_id: str, topic: str) -> None:
        import slack_sdk.errors
        try:
            self._client.conversations_setTopic(channel=room_id, topic=topic)
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error setting topic for {room_id}: {error}")

    def send_text(self, room_id: str, text: str) -> str:
        import slack_sdk.errors
        try:
            resp = self._client.chat_postMessage(channel=room_id, text=text)
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending message to {room_id}: {error}")
            return ""

    def pin_message(self, room_id: str, event_id: str) -> None:
        import slack_sdk.errors
        try:
            self._client.pins_add(channel=room_id, timestamp=event_id)
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error pinning message in {room_id}: {error}")

    def add_bookmark(self, room_id: str, title: str, url: str, emoji: str = "") -> None:
        import slack_sdk.errors
        try:
            self._client.bookmarks_add(
                channel_id=room_id,
                title=title,
                type="link",
                link=url,
                emoji=emoji if emoji else None,
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error adding bookmark to {room_id}: {error}")

    def invite_user(self, room_id: str, user_id: str) -> None:
        from incidentbot.slack.client import invite_user_to_channel
        invite_user_to_channel(channel_id=room_id, user=user_id)

    def invite_users(self, room_id: str, user_ids: list[str]) -> None:
        import slack_sdk.errors
        if not user_ids:
            return
        try:
            self._client.conversations_invite(
                channel=room_id, users=",".join(user_ids)
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error inviting users to {room_id}: {error}")

    def get_group_members_by_name(self, group_name: str) -> list[str]:
        import slack_sdk.errors
        groups = self._workspace_groups.get("usergroups", [])
        matched = [g for g in groups if g["handle"] == group_name]
        if not matched:
            logger.warning(f"Slack usergroup '{group_name}' not found")
            return []
        try:
            resp = self._client.usergroups_users_list(usergroup=matched[0]["id"])
            return resp.get("users", [])
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error getting members for group '{group_name}': {error}")
            return []

    def get_user_display_name(self, user_id: str) -> str:
        from incidentbot.slack.client import get_slack_user
        return get_slack_user(user_id).get("real_name", "Unknown")

    def room_url(self, room_id: str) -> str:
        return f"https://{self._workspace_id}.slack.com/archives/{room_id}"

    def post_incident_boilerplate(self, incident: Any) -> str:
        import slack_sdk.errors
        from incidentbot.slack.messages import BlockBuilder
        try:
            resp = self._client.chat_postMessage(
                **BlockBuilder.boilerplate_message(incident=incident),
                text="Incident details have been posted to an incident channel.",
            )
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending boilerplate message: {error}")
            return ""

    def post_welcome_message(self, room_id: str) -> None:
        import slack_sdk.errors
        from incidentbot.slack.messages import BlockBuilder
        try:
            self._client.chat_postMessage(
                channel=room_id,
                blocks=BlockBuilder.welcome_message(),
                text="Welcome to this incident channel.",
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending welcome message to {room_id}: {error}")

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
        import slack_sdk.errors
        from incidentbot.slack.messages import IncidentChannelDigestNotification
        try:
            resp = self._client.chat_postMessage(
                **IncidentChannelDigestNotification.create(
                    channel_id=channel_id,
                    has_private_channel=has_private_channel,
                    incident_components=incident_components,
                    incident_description=incident_description,
                    incident_impact=incident_impact,
                    incident_slug=incident_slug,
                    initial_status=initial_status,
                    meeting_link=meeting_link,
                    severity=severity,
                ),
                text="A new incident has been declared!",
            )
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error sending digest notification: {error}")
            return ""

    def post_jira_issue(
        self, room_id: str, key: str, summary: str, issue_type: str, link: str
    ) -> str:
        import slack_sdk.errors
        from incidentbot.slack.messages import BlockBuilder
        try:
            resp = self._client.chat_postMessage(
                channel=room_id,
                blocks=BlockBuilder.jira_issue_message(
                    key=key, summary=summary, type=issue_type, link=link
                ),
                text=f"A Jira issue has been created: {key}",
            )
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error posting Jira issue to {room_id}: {error}")
            return ""

    def post_gitlab_incident(
        self, room_id: str, incident_id: int, summary: str, link: str
    ) -> str:
        import slack_sdk.errors
        from incidentbot.slack.messages import BlockBuilder
        try:
            resp = self._client.chat_postMessage(
                channel=room_id,
                blocks=BlockBuilder.gitlab_incident_message(
                    id=incident_id, summary=summary, link=link
                ),
                text="A GitLab incident has been created.",
            )
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error posting GitLab incident to {room_id}: {error}")
            return ""

    def post_statuspage_prompt(self, room_id: str) -> None:
        import slack_sdk.errors
        from incidentbot.statuspage.slack import return_new_statuspage_incident_message
        try:
            self._client.chat_postMessage(
                **return_new_statuspage_incident_message(channel_id=room_id),
                text="Statuspage prompt has been posted.",
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"Error posting Statuspage prompt to {room_id}: {error}")
