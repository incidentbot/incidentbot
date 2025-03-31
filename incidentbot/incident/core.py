from datetime import datetime
import asyncio
import re
import slack_sdk.errors

from incidentbot.configuration.settings import settings
from incidentbot.incident.event import EventLogHandler
from incidentbot.incident.util import comms_reminder, role_watcher
from incidentbot.logging import logger
from incidentbot.models.database import IncidentRecord, engine
from incidentbot.models.pager import read_pager_auto_page_targets
from incidentbot.scheduler.core import (
    process as TaskScheduler,
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
    from incidentbot.scheduler.core import process as TaskScheduler
    from incidentbot.slack.client import invite_user_to_channel
    from incidentbot.slack.client import (
        all_workspace_groups,
        get_slack_user,
        slack_web_client,
        slack_workspace_id,
    )


def format_channel_name(id: int,
                        description: str,
                        use_date_prefix: bool = False,
                        comms: bool = False) -> str:
    """
    Format a channel name by removing special characters, replacing spaces with dashes,
    and optionally adding a date prefix.

    Args:
        id (int): The identifier for the channel.
        description (str): A description used for the channel name.
        use_date_prefix (bool): Whether to prepend the current date to the name. Defaults to False.
        comms (bool): Whether to append '-comms' to the name. Defaults to False.

    Returns:
        str: The formatted channel name.
    """

    # Prepare prefix and suffix
    prefix = settings.options.channel_name_prefix
    suffix = re.sub(
        r"[^A-Za-z0-9\s]",
        "",
        description,
    )

    # Replace spaces with dashes and convert to lowercase
    suffix = suffix.replace(" ", "-").lower()

    # Handle date prefix if required
    current_date = ""
    if use_date_prefix:
        date_format = settings.options.channel_name_date_format.replace(
            "YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
        current_date = datetime.now().strftime(date_format)
        # Construct the final channel name
        final = f"{prefix}-{id}-{current_date}-{suffix}"
    else:
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
    incident_impact: str | None = None
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

    def __init__(self, params: IncidentRequestParameters | None = None):
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
                    id=record.id,
                    description=self.params.incident_description,
                    use_date_prefix=settings.options.channel_name_use_date_prefix
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
                record.has_private_channel = (
                    self.params.private_channel
                    or self.params.is_security_incident
                )
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
                            has_private_channel=record.has_private_channel,
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
                Create bookmark for meeting (optional)
                """

                if record.meeting_link:
                    try:
                        # Try to sort out the meeting link provider
                        meeting_link_provider = "Audio"
                        if "zoom" in record.meeting_link.lower():
                            meeting_link_provider = "Zoom"

                        slack_web_client.bookmarks_add(
                            channel_id=record.channel_id,
                            emoji=settings.icons.get(settings.platform).get(
                                "meeting"
                            ),
                            title=f"{meeting_link_provider} Meeting",
                            type="link",
                            link=record.meeting_link,
                        )
                    except slack_sdk.errors.SlackApiError as error:
                        logger.error(
                            f"Error adding meeting bookmark to channel: {error}"
                        )

                """
                Pin meeting link to channel (optional)
                """

                if (
                    record.meeting_link
                    and settings.options.pin_meeting_link_to_channel
                ):
                    try:
                        resp = slack_web_client.chat_postMessage(
                            channel=record.channel_id,
                            text=f"Join the meeting here: {record.meeting_link}",
                        )
                        slack_web_client.pins_add(
                            channel=record.channel_id,
                            timestamp=resp["ts"],
                        )
                    except slack_sdk.errors.SlackApiError as error:
                        logger.error(
                            f"Error pinning meeting link to channel: {error}"
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
                        get_slack_user(self.params.user).get(
                            "real_name", "NotAvailable"
                        )
                    ),
                    incident_id=record.id,
                    incident_slug=record.slug,
                    source="system",
                    user=get_slack_user(self.params.user).get(
                        "real_name", "NotAvailable"
                    ),
                )

                return f"<#{record.channel_id}>"
        except Exception as error:
            logger.error(f"Error during incident creation: {error}")
            return

    @staticmethod
    def delete(id: int) -> bool:
        """
        Delete an incident
        """

        try:
            with Session(engine) as session:
                # Remove record
                record = session.exec(
                    select(IncidentRecord).filter(IncidentRecord.id == id)
                ).one()
                session.delete(record)
                session.commit()

                # Clean up jobs
                for job in TaskScheduler.list_jobs():
                    if f"inc-{record.id}" in job.id:
                        TaskScheduler.delete_job(job.id)

                slack_web_client.chat_postMessage(
                    channel=record.channel_id,
                    text=":octagonal_sign: This incident has been deleted from the application. "
                    + "You will no longer be able to use the bot to manage it.",
                )

                return True
        except Exception as error:
            logger.error(f"Error deleting incident: {error}")
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
                    if (
                        record.severity in gr.severities.split(",")
                        or gr.severities == "all"
                    ):
                        # Get group members
                        try:
                            required_participants_group_members = (
                                slack_web_client.usergroups_users_list(
                                    usergroup=[
                                        g
                                        for g in all_workspace_groups.get(
                                            "usergroups"
                                        )
                                        if g["handle"] == gr.name
                                    ][0]["id"],
                                )
                            )["users"]
                        except Exception as error:
                            logger.error(
                                f"Error getting group members for {gr.name}: {error}"
                            )
                            raise

                        # Invite group members to channel
                        try:
                            slack_web_client.conversations_invite(
                                channel=record.channel_id,
                                users=",".join(
                                    required_participants_group_members
                                ),
                            )

                            # Write event log
                            EventLogHandler.create(
                                event=f"Group {gr.name} was invited to the incident channel based on configured settings",
                                incident_id=record.id,
                                incident_slug=record.slug,
                                source="system",
                            )
                        except slack_sdk.errors.SlackApiError as error:
                            logger.error(
                                f"Error when inviting auto users: {error}"
                            )

                        # If the PagerDuty integration is enabled
                        # and the group declaration has an escalation
                        # issue a page
                        if (
                            settings.integrations
                            and settings.integrations.pagerduty
                            and settings.integrations.pagerduty.enabled
                            and gr.pagerduty_escalation_policy
                        ):
                            from incidentbot.pagerduty.api import (
                                PagerDutyInterface,
                            )

                            pagerduty_interface = PagerDutyInterface(
                                escalation_policy=gr.pagerduty_escalation_policy
                            )

                            pagerduty_interface.page(
                                priority=gr.pagerduty_escalation_priority,
                                channel_name=record.channel_name,
                                channel_id=record.channel_id,
                                paging_user="auto",
                            )

                            # Write event log
                            EventLogHandler.create(
                                event="Created PagerDuty incident based on automatic configuration",
                                incident_id=record.id,
                                incident_slug=record.slug,
                                source="system",
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

                if auto_page_targets:
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
                        text=":warning: This incident was flagged as a security incident and the channel is private. You must invite other users to this channel manually.",
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
                            use_date_prefix=settings.options.channel_name_use_date_prefix,
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
                logger.error(f"Error adding job: {error}")

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
                logger.error(f"Error adding job: {error}")

            """
            Additional welcome messages
            """

            try:
                if settings.options.additional_welcome_messages:
                    for entry in settings.options.additional_welcome_messages:
                        resp = slack_web_client.chat_postMessage(
                            channel=record.channel_id,
                            text=entry.message,
                        )
                        if entry.pin:
                            slack_web_client.pins_add(
                                channel=record.channel_id,
                                timestamp=resp["ts"],
                            )
            except Exception as error:
                logger.error(
                    f"Error sending additional welcome message to {record.slug}: {error}"
                )

            """
            Final mutation
            """

            session.add(record)
            session.commit()
