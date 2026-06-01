from incidentbot.logging import logger
from incidentbot.platform.base import PlatformAdapter
from typing import Any


class SlackAdapter(PlatformAdapter):
    """Wraps the existing Slack SDK client into the PlatformAdapter interface."""

    def __init__(self):
        from incidentbot.slack.client import (
            slack_web_client,
            slack_workspace_id,
            all_workspace_groups,
        )

        self._client = slack_web_client
        self._workspace_id = slack_workspace_id
        self._workspace_groups = all_workspace_groups

    def create_room(self, name: str, topic: str = "", private: bool = False) -> dict:
        import slack_sdk.errors

        logger.info("creating slack channel", name=name)
        try:
            resp = self._client.conversations_create(name=name, is_private=private)
            channel = resp.get("channel")
            return {"id": channel["id"], "name": channel["name"]}
        except slack_sdk.errors.SlackApiError as error:
            if error.response.get("error") == "name_taken":
                # Channel already exists (e.g. from a previous failed attempt).
                # Locate it and return it so incident creation can continue.
                logger.warning(
                    "channel already exists, looking up existing channel", name=name
                )
                return self._find_channel_by_name(name)
            logger.exception("error creating channel", name=name, error=error)
            return {}

    def _find_channel_by_name(self, name: str) -> dict:
        """Look up an existing Slack channel by name; unarchive it if necessary."""
        import slack_sdk.errors
        from incidentbot.slack.client import get_slack_channel_list_db
        from incidentbot.util import gen

        # Fast path: check the cached channel list
        channels = get_slack_channel_list_db() or []
        idx = gen.find_index_in_list(channels, "name", name)
        if idx != -1:
            ch = channels[idx]
            return {"id": ch["id"], "name": ch["name"]}

        # Slow path: walk the full list including archived channels
        try:
            cursor = None
            while True:
                kwargs = {"exclude_archived": False, "limit": 1000}
                if cursor:
                    kwargs["cursor"] = cursor
                resp = self._client.conversations_list(**kwargs)
                for ch in resp.get("channels", []):
                    if ch.get("name") == name:
                        if ch.get("is_archived"):
                            logger.info("unarchiving existing channel", name=name, channel_id=ch["id"])
                            self._client.conversations_unarchive(channel=ch["id"])
                        return {"id": ch["id"], "name": ch["name"]}
                cursor = resp.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error looking up existing channel", name=name, error=error)

        logger.error("could not locate existing channel, incident creation will fail", name=name)
        return {}

    def set_room_topic(self, room_id: str, topic: str) -> None:
        import slack_sdk.errors

        try:
            self._client.conversations_setTopic(channel=room_id, topic=topic)
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error setting topic", room_id=room_id, error=error)

    def send_text(self, room_id: str, text: str) -> str:
        import slack_sdk.errors

        try:
            resp = self._client.chat_postMessage(channel=room_id, text=text)
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error sending message", room_id=room_id, error=error)
            return ""

    def pin_message(self, room_id: str, event_id: str) -> None:
        import slack_sdk.errors

        try:
            self._client.pins_add(channel=room_id, timestamp=event_id)
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error pinning message", room_id=room_id, error=error)

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
            logger.exception("error adding bookmark", room_id=room_id, error=error)

    def invite_user(self, room_id: str, user_id: str) -> None:
        from incidentbot.slack.client import invite_user_to_channel

        invite_user_to_channel(channel_id=room_id, user=user_id)

    def invite_users(self, room_id: str, user_ids: list[str]) -> None:
        import slack_sdk.errors

        if not user_ids:
            return
        try:
            self._client.conversations_invite(channel=room_id, users=",".join(user_ids))
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error inviting users", room_id=room_id, error=error)

    def make_room_admin(self, room_id: str, user_id: str) -> None:
        # Slack channels do not have a room-admin concept analogous to Matrix power levels.
        return

    def get_group_members_by_name(self, group_name: str) -> list[str]:
        import slack_sdk.errors

        groups = self._workspace_groups.get("usergroups", [])
        matched = [g for g in groups if g["handle"] == group_name]
        if not matched:
            logger.warning("slack usergroup not found", group_name=group_name)
            return []
        try:
            resp = self._client.usergroups_users_list(usergroup=matched[0]["id"])
            return resp.get("users", [])
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error getting members for group", group_name=group_name, error=error)
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
            logger.exception("error sending boilerplate message", error=error)
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
            logger.exception("error sending welcome message", room_id=room_id, error=error)

    def post_roles_panel(self, room_id: str, incident: Any, participants: list) -> str:
        import slack_sdk.errors
        from incidentbot.slack.messages import BlockBuilder

        try:
            resp = self._client.chat_postMessage(
                channel=room_id,
                blocks=BlockBuilder.roles_panel(
                    incident=incident, participants=participants
                ),
                text="Role assignments for this incident.",
            )
            return resp.get("ts", "")
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error posting roles panel", room_id=room_id, error=error)
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
            logger.exception("error sending digest notification", error=error)
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
            logger.exception("error posting jira issue", room_id=room_id, error=error)
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
            logger.exception("error posting gitlab incident", room_id=room_id, error=error)
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
            logger.exception("error posting statuspage prompt", room_id=room_id, error=error)

    def post_phare_prompt(self, room_id: str) -> None:
        import slack_sdk.errors
        from incidentbot.phare.slack import return_new_phare_incident_message

        try:
            self._client.chat_postMessage(
                **return_new_phare_incident_message(channel_id=room_id),
                text="Phare prompt has been posted to an incident.",
            )
        except slack_sdk.errors.SlackApiError as error:
            logger.exception("error posting phare prompt", room_id=room_id, error=error)
