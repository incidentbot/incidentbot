from datetime import datetime
import asyncio
import re

from incidentbot.configuration.settings import settings
from incidentbot.incident.event import EventLogHandler
from incidentbot.incident.automations import run as run_automations
from incidentbot.incident.reminders import register_reminder_jobs
from incidentbot.logging import logger
from incidentbot.models.database import IncidentRecord, engine
from incidentbot.models.pager import read_pager_auto_page_targets
from incidentbot.platform import get_adapter
from incidentbot.scheduler.core import (
    process as TaskScheduler,
)
from incidentbot.zoom.meeting import ZoomMeeting
from pydantic import BaseModel
from sqlmodel import Session, select


def format_channel_name(
    id: int,
    description: str,
    use_date_prefix: bool = False,
    comms: bool = False,
) -> str:
    """
    Format a channel name by removing special characters, replacing spaces with dashes,
    and optionally adding a date prefix.
    """

    prefix = settings.options.channel_name_prefix
    suffix = re.sub(r"[^A-Za-z0-9\s]", "", description)
    suffix = suffix.replace(" ", "-").lower()

    current_date = ""
    if use_date_prefix:
        date_format = (
            settings.options.channel_name_date_format.replace("YYYY", "%Y")
            .replace("MM", "%m")
            .replace("DD", "%d")
        )
        current_date = datetime.now().strftime(date_format)
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

        adapter = get_adapter()

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
                    status=next(
                        (status for status, config in settings.statuses.items() if config.initial),
                        list(settings.statuses.keys())[0] if settings.statuses else None
                    ),
                    statuses=[status for status in settings.statuses],
                )

                session.add(record)
                session.commit()
                session.refresh(record)

                """
                Create platform room/channel for incident
                """

                channel_name = format_channel_name(
                    id=record.id,
                    description=self.params.incident_description,
                    use_date_prefix=settings.options.channel_name_use_date_prefix,
                )
                channel = adapter.create_room(
                    name=channel_name,
                    private=self.params.private_channel | self.params.is_security_incident,
                )
                meeting_link = self.generate_meeting_link(channel_name=channel_name)

                """
                Update record
                """

                channel_id = channel.get("id")
                if not channel_id:
                    # Channel creation failed entirely — delete the stub record so we
                    # don't leave an orphaned row with channel_id=None in the DB.
                    session.delete(record)
                    session.commit()
                    logger.error(
                        "aborting incident creation: could not obtain a channel id", channel_name=channel_name
                    )
                    return None

                # Guard against duplicate records pointing at the same channel (e.g. a
                # previous failed attempt that did successfully create the Slack channel).
                duplicate = session.exec(
                    select(IncidentRecord).filter(
                        IncidentRecord.channel_id == channel_id,
                        IncidentRecord.id != record.id,
                    )
                ).first()
                if duplicate:
                    session.delete(record)
                    session.commit()
                    logger.warning(
                        "channel already has an incident record, reusing existing incident",
                        channel_id=channel_id,
                        existing_slug=duplicate.slug,
                    )
                    return channel_id

                record.channel_id = channel_id
                record.channel_name = channel_name
                record.has_private_channel = (
                    self.params.private_channel or self.params.is_security_incident
                )

                if settings.platform == "matrix" and self.params.user:
                    adapter.invite_user(record.channel_id, self.params.user)
                    adapter.make_room_admin(record.channel_id, self.params.user)
                record.link = adapter.room_url(channel.get("id"))
                record.meeting_link = meeting_link
                record.slug = f"{settings.options.channel_name_prefix}-{record.id}"

                """
                Notify digest room/channel
                """

                logger.info(
                    "sending message to digest channel", channel=record.channel_name
                )
                digest_event_id = adapter.post_digest_notification(
                    channel_id=record.channel_id,
                    has_private_channel=record.has_private_channel,
                    incident_components=record.components,
                    incident_description=record.description,
                    incident_impact=record.impact,
                    incident_slug=f"{settings.options.channel_name_prefix}-{record.id}",
                    initial_status=record.status,
                    meeting_link=record.meeting_link,
                    severity=record.severity,
                )

                record.digest_message_ts = digest_event_id

                """
                Set incident room topic
                """

                adapter.set_room_topic(
                    room_id=record.channel_id,
                    topic=f"Severity: {record.severity.upper()} | Status: {record.status.title()}",
                )

                """
                Send boilerplate info to incident room
                """

                bp_event_id = adapter.post_incident_boilerplate(incident=record)
                record.boilerplate_message_ts = bp_event_id

                """
                Send welcome message to incident room
                """

                adapter.post_welcome_message(room_id=record.channel_id)

                """
                Post live roles panel (updated in-place as roles are claimed)
                """

                roles_panel_ts = adapter.post_roles_panel(
                    room_id=record.channel_id,
                    incident=record,
                    participants=[],
                )
                if roles_panel_ts:
                    from incidentbot.models.database import ApplicationData

                    with Session(engine) as sess:
                        sess.add(
                            ApplicationData(
                                name=f"role_panel_{record.channel_id}",
                                json_data={"ts": roles_panel_ts},
                            )
                        )
                        sess.commit()

                if (
                    settings.platform == "matrix"
                    and settings.matrix
                    and settings.matrix.widget_base_url
                ):
                    from incidentbot.util.widget_token import build_widget_url

                    widget_url = build_widget_url(
                        settings.matrix.widget_base_url,
                        "/widget/incident-room",
                        record.channel_id,
                        "incidentbot-controls",
                    )
                    try:
                        adapter.client.register_widget(
                            room_id=record.channel_id,
                            widget_id="incidentbot-controls",
                            name="Incident Controls",
                            url=widget_url,
                        )
                        logger.info(
                            "incident controls widget registered in room", room_id=record.channel_id
                        )
                    except Exception as error:
                        logger.exception(
                            "failed to register incident controls widget", room_id=record.channel_id, error=error
                        )

                """
                Add meeting bookmark (optional)
                """

                if record.meeting_link:
                    meeting_link_provider = "Audio"
                    if "zoom" in record.meeting_link.lower():
                        meeting_link_provider = "Zoom"

                    adapter.add_bookmark(
                        room_id=record.channel_id,
                        title=f"{meeting_link_provider} Meeting",
                        url=record.meeting_link,
                        emoji=settings.icons.get(settings.platform, {}).get("meeting", ""),
                    )

                """
                Pin meeting link to channel (optional)
                """

                if record.meeting_link and settings.options.pin_meeting_link_to_channel:
                    event_id = adapter.send_text(
                        room_id=record.channel_id,
                        text=f"Join the meeting here: {record.meeting_link}",
                    )
                    if event_id:
                        adapter.pin_message(room_id=record.channel_id, event_id=event_id)

                """
                Database commit
                """

                session.add(record)
                session.commit()

                """
                Run additional features
                """

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.handle_incident_optional_features(id=record.id))
                except RuntimeError:
                    asyncio.run(self.handle_incident_optional_features(id=record.id))

                # Invite the user who started the incident to the room
                if self.params.user:
                    logger.info(
                        "inviting declaring user to incident room",
                        user=self.params.user,
                        room_id=record.channel_id,
                    )
                    adapter.invite_user(room_id=record.channel_id, user_id=self.params.user)
                    try:
                        adapter.make_room_admin(
                            room_id=record.channel_id, user_id=self.params.user
                        )
                        logger.info(
                            "granted room admin to declaring user",
                            user=self.params.user,
                            room_id=record.channel_id,
                        )
                    except Exception as error:
                        logger.exception(
                            "failed to grant room admin to declaring user",
                            user=self.params.user,
                            room_id=record.channel_id,
                            error=error,
                        )
                else:
                    logger.info(
                        "no declaring user provided for incident, skipping auto-invite",
                        room_id=record.channel_id,
                    )

                # Write event log
                user_name = (
                    adapter.get_user_display_name(self.params.user)
                    if self.params.user
                    else "system"
                )
                EventLogHandler.create(
                    event=f"The incident was reported by {user_name}",
                    incident_id=record.id,
                    incident_slug=record.slug,
                    source="system",
                    user=user_name,
                )

                return record.channel_id
        except Exception as error:
            logger.exception("error during incident creation", error=error)
            return

    @staticmethod
    def delete(id: int) -> bool:
        """
        Delete an incident
        """

        try:
            adapter = get_adapter()
            with Session(engine) as session:
                record = session.exec(
                    select(IncidentRecord).filter(IncidentRecord.id == id)
                ).one()
                session.delete(record)
                session.commit()

                for job in TaskScheduler.list_jobs():
                    if f"inc-{record.id}" in job.id:
                        TaskScheduler.delete_job(job.id)

                adapter.send_text(
                    room_id=record.channel_id,
                    text=(
                        "This incident has been deleted from the application. "
                        "You will no longer be able to use the bot to manage it."
                    ),
                )

                return True
        except Exception as error:
            logger.exception("error deleting incident", error=error)
            return

    async def handle_incident_optional_features(self, id: int):
        """
        Run optional post-creation features: group invites, Statuspage, PagerDuty,
        Jira, GitLab, comms channel, schedulers, additional messages.
        """

        adapter = get_adapter()

        with Session(engine) as session:
            record = session.exec(
                select(IncidentRecord).filter(IncidentRecord.id == id)
            ).one()

            run_automations("on_open", record)

            """
            Post prompt for creating Statuspage incident if enabled (optional)
            """

            if (
                settings.integrations
                and settings.integrations.atlassian
                and settings.integrations.atlassian.statuspage
                and settings.integrations.atlassian.statuspage.enabled
            ):
                logger.info("sending statuspage prompt", channel=record.channel_name)
                adapter.post_statuspage_prompt(room_id=record.channel_id)

            """
            Post prompt for creating Phare incident if enabled (optional)
            """

            if (
                settings.integrations
                and settings.integrations.phare
                and settings.integrations.phare.enabled
            ):
                logger.info("sending phare prompt", channel=record.channel_name)
                adapter.post_phare_prompt(record.channel_id)

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
                            logger.info("paging team", team=k)
                            pagerduty_interface = PagerDutyInterface(escalation_policy=v)
                            pagerduty_interface.page(
                                priority="low",
                                channel_name=record.channel_name,
                                channel_id=record.channel_id,
                                paging_user="auto",
                            )
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
                adapter.send_text(
                    room_id=record.channel_id,
                    text=(
                        "This incident was flagged as a security incident and the channel is private. "
                        "You must invite other users to this channel manually."
                    ),
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

                        try:
                            event_id = adapter.post_jira_issue(
                                room_id=record.channel_id,
                                key=resp.get("key"),
                                summary=record.description,
                                issue_type=settings.integrations.atlassian.jira.auto_create_issue_type,
                                link=issue_link,
                            )
                            if event_id:
                                adapter.pin_message(
                                    room_id=record.channel_id, event_id=event_id
                                )
                        except Exception as error:
                            logger.exception(
                                "error sending jira issue message", channel=record.channel_name, error=error
                            )
                except Exception as error:
                    logger.exception(
                        "error creating jira incident", channel=record.channel_name, error=error
                    )

            """
            If a Gitlab issue should be created automatically, create it (optional)
            """

            if (
                settings.integrations
                and settings.integrations.gitlab
                and settings.integrations.gitlab.enabled
                and settings.integrations.gitlab.auto_create_incident
            ):
                from incidentbot.gitlab.issue import GitLabIncident
                from incidentbot.models.database import GitlabIssueRecord

                try:
                    issue_obj = GitLabIncident(
                        description=record.channel_name,
                        incident_id=record.id,
                        summary=record.description,
                        status=record.status,
                        severity=record.severity,
                    )
                    resp = issue_obj.new()

                    if resp is not None:
                        issue_link = resp.get("web_url")
                        gitlab_incident_record = GitlabIssueRecord(
                            id=resp.get("id"),
                            iid=resp.get("iid"),
                            parent=record.id,
                            status="Unassigned",
                            url=issue_link,
                        )
                        session.add(gitlab_incident_record)

                        try:
                            event_id = adapter.post_gitlab_incident(
                                room_id=record.channel_id,
                                incident_id=resp.get("id"),
                                summary=record.description,
                                link=issue_link,
                            )
                            if event_id:
                                adapter.pin_message(
                                    room_id=record.channel_id, event_id=event_id
                                )
                        except Exception as error:
                            logger.exception(
                                "error sending gitlab incident message", channel=record.channel_name, error=error
                            )
                except Exception as error:
                    logger.exception(
                        "error creating gitlab incident", channel=record.channel_name, error=error
                    )

            """
            Additional comms channel (optional)
            """

            if record.additional_comms_channel:
                try:
                    comms_channel = adapter.create_room(
                        name=format_channel_name(
                            id=record.id,
                            description=record.description,
                            use_date_prefix=settings.options.channel_name_use_date_prefix,
                            comms=True,
                        ),
                        private=False,
                    )
                    comms_id = comms_channel.get("id")
                    event_id = adapter.send_text(
                        room_id=record.channel_id,
                        text=f"Dedicated communications channel/room: {adapter.room_url(comms_id)}",
                    )
                    if event_id:
                        adapter.pin_message(room_id=record.channel_id, event_id=event_id)

                    record.additional_comms_channel_id = comms_id
                    record.additional_comms_channel_link = adapter.room_url(comms_id)
                except Exception as error:
                    logger.exception("error creating comms channel", error=error)

            """
            Register per-incident reminder jobs
            """

            try:
                register_reminder_jobs(record)
            except Exception as error:
                logger.exception("error registering reminder jobs", error=error)

            """
            Additional welcome messages
            """

            try:
                if settings.options.additional_welcome_messages:
                    for entry in settings.options.additional_welcome_messages:
                        event_id = adapter.send_text(
                            room_id=record.channel_id, text=entry.message
                        )
                        if entry.pin and event_id:
                            adapter.pin_message(
                                room_id=record.channel_id, event_id=event_id
                            )
            except Exception as error:
                logger.exception(
                    "error sending additional welcome message", slug=record.slug, error=error
                )

            """
            Final mutation
            """

            session.add(record)
            session.commit()
