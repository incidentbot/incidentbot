import asyncio
import re
import slack_sdk.errors

from incidentbot.configuration.settings import settings
from incidentbot.incident.event import EventLogHandler
from incidentbot.incident.util import comms_reminder, role_watcher
from incidentbot.logging import logger
from incidentbot.models.database import IncidentRecord, engine
from incidentbot.models.pager import read_pager_auto_page_targets
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.slack.client import (
    all_workspace_groups,
    get_slack_user,
    slack_web_client,
    slack_workspace_id,
)
from incidentbot.slack.messages import (
    BlockBuilder,
    IncidentChannelDigestNotification,
)
from incidentbot.statuspage.slack import return_new_statuspage_incident_message
from incidentbot.zoom.meeting import ZoomMeeting
from pydantic import BaseModel
from sqlmodel import Session, select

if not settings.IS_TEST_ENVIRONMENT:
    from incidentbot.slack.client import invite_user_to_channel


def format_channel_name(id: int, description: str, comms: bool = False) -> str:
    """
    Remove any special characters (allow only alphanumeric)
    """

    prefix = settings.options.channel_name_prefix
    suffix = re.sub(
        "[^A-Za-z0-9\\s]",
        "",
        description,
    )

    # Replace any spaces with dashes
    suffix = suffix.replace(" ", "-").lower()

    final = f"{prefix}-{id}-{suffix}"

    if comms:
        return f"{final}-comms"

    return final


class IncidentRequestParameters(BaseModel):
    """
    Base incident creation details
    """

    additional_comms_channel: bool | None = False
    created_from_web: bool | None = False
    incident_components: str
    incident_description: str
    incident_impact: str
    is_security_incident: bool | None = False
    private_channel: bool | None = False
    severity: str
    user: str | None = None


class Incident:
    """
    Instantiates an incident

    Parameters:
        params (IncidentRequestParameters)
    """

    def __init__(self, params: IncidentRequestParameters):
        self.params = params

    def create_channel(self, channel_name: str, private: bool = False) -> dict:
        """
        Create a Slack channel
        """

        logger.info(f"Creating Slack channel: {channel_name}")

        try:
            channel = slack_web_client.conversations_create(
                name=channel_name,
                is_private=private,
            )

            return channel.get("channel")
        except slack_sdk.errors.SlackApiError as error:
            logger.error(f"error creating channel {channel_name}: {error}")
            return

    def generate_meeting_link(self, channel_name: str) -> str | None:
        if (
            settings.integrations
            and settings.integrations.zoom
            and settings.integrations.zoom.enabled
        ):
            return ZoomMeeting(incident=channel_name).url
        else:
            return (
                settings.options.meeting_link
                if settings.options.meeting_link
                else None
            )

    def start(self) -> str:
        """
        Create an incident
        """

        # Create initial record
        try:
            with Session(engine) as session:
                record = IncidentRecord(
                    additional_comms_channel=self.params.additional_comms_channel,
                    components=self.params.incident_components,
                    description=self.params.incident_description,
                    impact=self.params.incident_impact,
                    is_security_incident=self.params.is_security_incident,
                    roles_all=[key for key, _ in settings.roles.items()],
                    severity=self.params.severity,
                    severities=[key for key, _ in settings.severities.items()],
                    status=[
                        status
                        for status, config in settings.statuses.items()
                        if config.initial
                    ][0],
                    statuses=[status for status in settings.statuses.keys()],
                )

                session.add(record)
                session.commit()
                session.refresh(record)

                """
                Create Slack channel for incident
                """

                channel_name = format_channel_name(
                    id=record.id, description=self.params.incident_description
                )
                channel = self.create_channel(
                    channel_name=channel_name,
                    private=self.params.private_channel
                    | self.params.is_security_incident,
                )
                meeting_link = self.generate_meeting_link(
                    channel_name=channel_name
                )

                """
                Update record
                """

                record.channel_id = channel.get("id")
                record.channel_name = channel_name
                record.link = "https://{}.slack.com/archives/{}".format(
                    slack_workspace_id, channel.get("id")
                )
                record.meeting_link = meeting_link
                record.slug = (
                    f"{settings.options.channel_name_prefix}-{record.id}"
                )

                """
                Notify incidents digest channel
                """

                logger.info(
                    f"Sending message to digest channel for: {record.channel_name}"
                )
                try:
                    digest_message = slack_web_client.chat_postMessage(
                        **IncidentChannelDigestNotification.create(
                            channel_id=record.channel_id,
                            incident_components=record.components,
                            incident_description=record.description,
                            incident_impact=record.impact,
                            incident_slug=f"{settings.options.channel_name_prefix}-{record.id}",
                            initial_status=record.status,
                            meeting_link=record.meeting_link,
                            severity=record.severity,
                        ),
                        text="A new incident has been declared!",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending message to incident digest channel: {error}"
                    )

                """
                Update record
                """

                record.digest_message_ts = digest_message.get("ts")

                """
                Set incident channel topic
                """

                try:
                    slack_web_client.conversations_setTopic(
                        channel=record.channel_id,
                        topic=f"Severity: {record.severity.upper()} | Status: {record.status.title()}",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error setting incident channel topic: {error}"
                    )

                """
                Send boilerplate info to incident channel
                """

                try:
                    bp_message = slack_web_client.chat_postMessage(
                        **BlockBuilder.boilerplate_message(
                            incident=record,
                        ),
                        text="Incident details have been posted to an incident channel.",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending message to incident channel: {error}"
                    )

                """
                Update record
                """

                record.boilerplate_message_ts = bp_message.get("ts")

                """
                Send welcome message to incident channel
                """

                try:
                    slack_web_client.chat_postMessage(
                        channel=record.channel_id,
                        blocks=BlockBuilder.welcome_message(),
                        text="Welcome Message",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending welcome message to incident channel: {error}"
                    )

                """
                Post meeting link in the channel upon creation (optional)
                """

                if record.meeting_link:
                    try:
                        meeting_link_message = slack_web_client.chat_postMessage(
                            channel=record.channel_id,
                            text="{} Please join the meeting here: {}".format(
                                settings.icons.get(settings.platform).get(
                                    "meeting"
                                ),
                                record.meeting_link,
                            ),
                            blocks=[
                                {
                                    "type": "header",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "{} Please join the meeting here.".format(
                                            settings.icons.get(
                                                settings.platform
                                            ).get("meeting")
                                        ),
                                    },
                                },
                                {"type": "divider"},
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": record.meeting_link,
                                    },
                                },
                            ],
                        )
                        slack_web_client.pins_add(
                            channel=record.channel_id,
                            timestamp=meeting_link_message["message"]["ts"],
                        )
                    except slack_sdk.errors.SlackApiError as error:
                        logger.error(
                            f"Error sending meeting link to channel: {error}"
                        )

                """
                Database commit
                """

                session.add(record)
                session.commit()

                """
                Run additional features
                """

                asyncio.run(
                    self.handle_incident_optional_features(id=record.id)
                )

                # Invite the user who started the incident to the channel
                invite_user_to_channel(
                    channel_id=record.channel_id, user=self.params.user
                )

                # Write event log
                EventLogHandler.create(
                    event="The incident was reported by {}".format(
                        (get_slack_user(self.params.user)["real_name"])
                    ),
                    incident_id=record.id,
                    incident_slug=record.slug,
                    source="system",
                    user=get_slack_user(self.params.user)["real_name"],
                )

                return f"<#{record.channel_id}>"
        except Exception as error:
            logger.error(f"Error during incident creation: {error}")
            return

    async def handle_incident_optional_features(self, id: int):
        """
        Invite required participants (optional)
        """

        with Session(engine) as session:
            record = session.exec(
                select(IncidentRecord).filter(IncidentRecord.id == id)
            ).one()

            if settings.options.auto_invite_groups:
                for gr in settings.options.auto_invite_groups:
                    all_groups = all_workspace_groups.get("usergroups")
                    if len(all_groups) == 0:
                        logger.error(
                            f"Error when inviting mandatory users: looked for group {gr} but did not find it."
                        )
                    else:
                        try:
                            required_participants_group = [
                                g for g in all_groups if g["handle"] == gr
                            ][0]["id"]
                            required_participants_group_members = (
                                slack_web_client.usergroups_users_list(
                                    usergroup=required_participants_group,
                                )
                            )["users"]
                        except Exception as error:
                            logger.error(
                                f"Error when formatting automatic invitees group name: {error}"
                            )
                        try:
                            invite = slack_web_client.conversations_invite(
                                channel=record.channel_id,
                                users=",".join(
                                    required_participants_group_members
                                ),
                            )
                            logger.debug(f"\n{invite}\n")

                            # Write event log
                            EventLogHandler.create(
                                event=f"Group {gr} was invited to the incident channel based on configured settings",
                                incident_id=record.id,
                                incident_slug=record.slug,
                                source="system",
                            )
                        except slack_sdk.errors.SlackApiError as error:
                            logger.error(
                                f"Error when inviting auto users: {error}"
                            )

            """
            Post prompt for creating Statuspage incident if enabled (optional)
            """

            if (
                settings.integrations
                and settings.integrations.atlassian
                and settings.integrations.atlassian.statuspage
                and settings.integrations.atlassian.statuspage.enabled
            ):
                sp_starter_message_content = (
                    return_new_statuspage_incident_message(
                        channel_id=record.channel_id
                    )
                )

                logger.info(
                    f"Sending Statuspage prompt to {record.channel_name}"
                )

                try:
                    slack_web_client.chat_postMessage(
                        **sp_starter_message_content,
                        text="Statuspage prompt has been posted to an incident.",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending Statuspage prompt to incident channel {record.channel_name}: {error}"
                    )

            """
            Page groups that are required to be automatically paged (optional)
            """

            if (
                settings.integrations
                and settings.integrations.pagerduty
                and settings.integrations.pagerduty.enabled
            ):
                from incidentbot.pagerduty.api import PagerDutyInterface

                auto_page_targets = read_pager_auto_page_targets()

                if len(auto_page_targets) != 0:
                    for i in auto_page_targets:
                        for k, v in i.items():
                            logger.info(f"Paging {k}...")

                            pagerduty_interface = PagerDutyInterface(
                                escalation_policy=v
                            )

                            pagerduty_interface.page(
                                priority="low",
                                channel_name=record.channel_name,
                                channel_id=record.channel_id,
                                paging_user="auto",
                            )

                            # Write event log
                            EventLogHandler.create(
                                event=f"Created PagerDuty incident for team {k} at user request",
                                incident_id=record.id,
                                incident_slug=record.slug,
                                source="system",
                            )

            """
            Provide additional information if this is a security incident (optional)
            """

            if record.is_security_incident:
                try:
                    slack_web_client.chat_postMessage(
                        channel=record.channel_id,
                        text=f":warning: This incident was flagged as a security incident and the channel is private. You must invite other users to this channel manually.",
                    )
                except slack_sdk.errors.SlackApiError as error:
                    logger.error(
                        f"Error sending additional information to the incident channel {record.channel_name}: {error}"
                    )

            """
            If a Jira issue should be created automatically, create it (optional)
            """

            if (
                settings.integrations
                and settings.integrations.atlassian
                and settings.integrations.atlassian.jira
                and settings.integrations.atlassian.jira.enabled
                and settings.integrations.atlassian.jira.auto_create_issue
            ):
                from incidentbot.jira.issue import JiraIssue
                from incidentbot.models.database import JiraIssueRecord

                try:
                    issue_obj = JiraIssue(
                        description=record.channel_name,
                        incident_id=record.id,
                        issue_type=settings.integrations.atlassian.jira.auto_create_issue_type,
                        summary=record.description,
                    )

                    resp = issue_obj.new()

                    if resp is not None:
                        issue_link = f"{settings.ATLASSIAN_API_URL}/browse/{resp.get('key')}"

                        jira_issue_record = JiraIssueRecord(
                            key=resp.get("key"),
                            parent=record.id,
                            status="Unassigned",
                            url=issue_link,
                        )

                        session.add(jira_issue_record)

                        from incidentbot.slack.messages import (
                            BlockBuilder,
                        )

                        try:
                            resp = slack_web_client.chat_postMessage(
                                channel=record.channel_id,
                                blocks=BlockBuilder.jira_issue_message(
                                    key=resp.get("key"),
                                    summary=record.description,
                                    type=settings.integrations.atlassian.jira.auto_create_issue_type,
                                    link=issue_link,
                                ),
                                text=f"A Jira issue has been created for this incident: {resp.get('self')}",
                            )
                            slack_web_client.pins_add(
                                channel=record.channel_id,
                                timestamp=resp["ts"],
                            )
                        except Exception as error:
                            logger.error(
                                f"Error sending Jira issue message for {record.channel_name}: {error}"
                            )
                except Exception as error:
                    logger.error(
                        f"Error creating Jira incident for {record.channel_name}: {error}"
                    )

            """
            Additional comms channel (optional)
            """

            if record.additional_comms_channel:
                try:
                    comms_channel = self.create_channel(
                        channel_name=format_channel_name(
                            id=record.id,
                            description=record.description,
                            comms=True,
                        ),
                        private=False,
                    )
                    resp = slack_web_client.chat_postMessage(
                        channel=record.channel_id,
                        text="As requested, here is the dedicated communications channel for this incident: <#{}>".format(
                            comms_channel.get("id")
                        ),
                    )
                    slack_web_client.pins_add(
                        channel=record.channel_id,
                        timestamp=resp["ts"],
                    )
                except Exception as error:
                    logger.error(f"Error creating comms channel: {error}")

                record.additional_comms_channel_id = comms_channel.get("id")
                record.additional_comms_channel_link = (
                    "https://{}.slack.com/archives/{}".format(
                        slack_workspace_id, comms_channel.get("id")
                    )
                )

            """
            Create task to remind channel about status updates
            """

            try:
                if settings.initial_comms_reminder_minutes != 0:
                    TaskScheduler.scheduler.add_job(
                        id=f"{record.slug}_comms_reminder",
                        func=comms_reminder,
                        args=[record.channel_id],
                        trigger="interval",
                        name=f"{record.slug}_comms_reminder",
                        minutes=settings.initial_comms_reminder_minutes,
                        replace_existing=True,
                    )
            except Exception as error:
                logger.error(f"error adding job: {error}")

            """
            Create task to watch for unassigned roles
            """

            try:
                if settings.initial_role_watcher_minutes != 0:
                    TaskScheduler.scheduler.add_job(
                        id=f"{record.slug}_role_watcher",
                        func=role_watcher,
                        args=[record.channel_id],
                        trigger="interval",
                        name=f"{record.slug}_role_watcher",
                        minutes=settings.initial_role_watcher_minutes,
                        replace_existing=True,
                    )
            except Exception as error:
                logger.error(f"error adding job: {error}")

            session.add(record)
            session.commit()
