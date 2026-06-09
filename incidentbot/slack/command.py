import asyncio

from datetime import datetime
from incidentbot.configuration.settings import settings
from incidentbot.incident.actions import (
    _is_confluence_postmortem_link,
    generate_postmortem,
    set_severity as set_incident_severity,
    set_status as set_incident_status,
    sync_postmortem,
)
from incidentbot.incident.event import EventLogHandler
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.slack import (
    CommandInvocation,
    SlackBlockActionsResponse,
    User,
)
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.slack.client import slack_web_client
from incidentbot.slack.handler import app
from incidentbot.slack.messages import BlockBuilder
from incidentbot.slack.postmortem_sync_guard import (
    begin_postmortem_sync,
    end_postmortem_sync,
)
from incidentbot.slack.util import parse_modal_values
from slack_sdk.errors import SlackApiError
from typing import Any


@app.command(settings.root_slash_command)
def handle_root_command(ack, body):
    ack()
    command = CommandInvocation(**body)

    match command.text:
        case "":
            try:
                slack_web_client.chat_postEphemeral(
                    channel=command.channel_id,
                    user=command.user_id,
                    text="Application main menu.",
                    blocks=command_blocks(root=True),
                )
            except SlackApiError as error:
                logger.exception(
                    "error sending message back to user via slash command invocation", error=error
                )
        case "this":
            if not body.get("channel_name").startswith(
                f"{settings.options.channel_name_prefix}-"
            ):
                try:
                    slack_web_client.chat_postEphemeral(
                        channel=command.channel_id,
                        user=command.user_id,
                        text="The `this` command should only be used from within an incident channel.",
                    )
                except SlackApiError as error:
                    logger.exception(
                        f"error sending message back to user via slash command invocation: {error}"
                    )
            else:
                try:
                    slack_web_client.chat_postEphemeral(
                        channel=command.channel_id,
                        user=command.user_id,
                        text="Options for managing this incident.",
                        blocks=command_blocks(this=True),
                    )
                except SlackApiError as error:
                    logger.exception(
                        f"error sending message back to user via slash command invocation: {error}"
                    )
        case _:
            try:
                slack_web_client.chat_postEphemeral(
                    channel=command.channel_id,
                    user=command.user_id,
                    text=f"I don't know the command `{command.text}`.",
                )
            except SlackApiError as error:
                logger.exception(
                    "error sending message back to user via slash command invocation", error=error
                )


def command_blocks(
    root: bool = False, this: bool = False
) -> list[dict[str, Any]]:
    """
    Blocks for command input
    """


    if root:
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "What would you like to do?",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Declare Incident",
                            "emoji": True,
                        },
                        "value": "show_declare_incident_modal",
                        "action_id": "declare_incident_modal",
                        "style": "danger",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "List Incidents",
                            "emoji": True,
                        },
                        "value": "show_list_incidents",
                        "action_id": "incident.list_incidents",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Send Incident Update",
                            "emoji": True,
                        },
                        "value": "show_incident_update_modal",
                        "action_id": "incident_update_modal",
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Tip: Run `{settings.root_slash_command} this` from inside an incident channel for incident-specific options.",
                    }
                ],
            },
        ]

    if this:
        return [
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Describe",
                            "emoji": True,
                        },
                        "value": "describe_this_incident",
                        "action_id": "incident.describe_this_incident",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Set Severity",
                            "emoji": True,
                        },
                        "value": "this_incident_set_severity_modal",
                        "action_id": "incident.set_this_severity_modal",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Set Status",
                            "emoji": True,
                        },
                        "value": "this_incident_set_this_status_modal",
                        "action_id": "incident.set_this_status_modal",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Responders",
                            "emoji": True,
                        },
                        "value": "this_incident_view_responders",
                        "action_id": "incident.view_responders",
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Events",
                            "emoji": True,
                        },
                        "value": "view_incident_events",
                        "action_id": "incident.view_events",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Postmortem",
                            "emoji": True,
                        },
                        "value": "sync_or_create_postmortem",
                        "action_id": "incident.sync_or_create_postmortem",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Get Help",
                            "emoji": True,
                        },
                        "value": "get_help_for_this_incident",
                        "action_id": "incident.get_help_for_this_incident",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Page On-call",
                            "emoji": True,
                        },
                        "action_id": "pager",
                    },
                ],
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Archive Channel",
                            "emoji": True,
                        },
                        "value": "archive_incident_channel",
                        "action_id": "incident.archive_incident_channel",
                        "style": "danger",
                        "confirm": {
                            "title": {
                                "type": "plain_text",
                                "text": "Archive this channel?",
                            },
                            "text": {
                                "type": "mrkdwn",
                                "text": "This will archive the incident channel. Make sure the incident is resolved and a postmortem has been created if needed.",
                            },
                            "confirm": {"type": "plain_text", "text": "Archive"},
                            "deny": {"type": "plain_text", "text": "Cancel"},
                            "style": "danger",
                        },
                    },
                ],
            },
        ]


"""
Command Modals and Actions
"""

"""
Incident Management
"""


# Describe


@app.action("incident.describe_this_incident")
def show_describe_incident(ack, body):
    """
    Provides the response for describing an incident
    """

    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    try:
        slack_web_client.chat_postMessage(
            channel=record.channel_id,
            text="Describe incident.",
            blocks=BlockBuilder.describe_message(incident=record),
        )

        return
    except SlackApiError as error:
        logger.exception("error sending describe message to slack", error=error)


# Severity


@app.action("incident.set_this_severity_modal")
def show_set_severity_modal(ack, body, client):
    """
    Provides the modal that will display for setting an incident's severity
    """

    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "incident.set_this_severity_modal",
            "title": {"type": "plain_text", "text": "Set severity"},
            "submit": {"type": "plain_text", "text": "Done"},
            "blocks": BlockBuilder.set_this_severity_modal(record),
        },
    )


@app.view("incident.set_this_severity_modal")
def handle_set_severity_submission(ack, body):
    """
    Handles incident.set_this_severity_modal
    """

    ack()

    channel_id = (
        body.get("view").get("blocks")[0].get("block_id").split("_")[-1]
    )
    parsed = parse_modal_values(body)
    user = User(**body.get("user"))

    asyncio.run(
        set_incident_severity(
            channel_id=channel_id,
            severity=parsed.get("incident.set_this_severity"),
            user=user,
        )
    )


@app.action("incident.set_this_severity")
def handle_severity_select(ack, body, logger):
    ack()
    logger.debug(body)


# Status


@app.action("incident.set_this_status_modal")
def show_set_status_modal(ack, body, client):
    """
    Provides the modal that will display for setting an incident's status
    """

    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "incident.set_this_status_modal",
            "title": {"type": "plain_text", "text": "Set status"},
            "submit": {"type": "plain_text", "text": "Done"},
            "blocks": BlockBuilder.set_this_status_modal(record=record),
        },
    )


@app.view("incident.set_this_status_modal")
def handle_set_status_submission(ack, body):
    """
    Handles incident.set_this_status_modal
    """

    ack()
    channel_id = (
        body.get("view").get("blocks")[0].get("block_id").split("_")[-1]
    )
    parsed = parse_modal_values(body)
    user = User(**body.get("user"))

    asyncio.run(
        set_incident_status(
            channel_id=channel_id,
            status=parsed.get("incident.set_this_status"),
            user=user,
        )
    )


@app.action("incident.set_this_status")
def handle_status_select(ack, body, logger):
    ack()
    logger.debug(body)


# Roles


@app.action("incident.view_responders")
def show_incident_responders(ack, body):
    """
    Provides the response for viewing an incident's responders
    """

    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    responders = IncidentDatabaseInterface.list_participants(incident=record)
    user = User(**body.get("user"))

    try:
        slack_web_client.chat_postEphemeral(
            channel=record.channel_id,
            user=user.id,
            text="Responders list.",
            blocks=BlockBuilder.responders_list(
                incident=record, responders=responders, user=user
            ),
        )

        return
    except SlackApiError as error:
        logger.exception("error sending responders list to slack", error=error)


# Tasks


@app.action("incident.show_tasks")
def show_tasks(ack, body):
    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    user = User(**body.get("user"))

    jobs = []
    for job in TaskScheduler.list_jobs():
        if record.slug in job.id:
            jobs.append(job)

    if jobs:
        try:
            slack_web_client.chat_postEphemeral(
                channel=record.channel_id,
                user=user.id,
                blocks=BlockBuilder.task_list(tasks=jobs),
                text="Jobs detail.",
            )

            return
        except SlackApiError as error:
            logger.exception("error sending responders list to slack", error=error)
    else:
        try:
            slack_web_client.chat_postEphemeral(
                channel=record.channel_id,
                user=user.id,
                text="There are currently no tasks associated with this incident.",
            )

            return
        except SlackApiError as error:
            logger.exception("error sending responders list to slack", error=error)


# Events


@app.action("incident.view_events")
def show_incident_events(ack, body):
    ack()

    channel_id = body.get("channel").get("id")
    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    events = EventLogHandler.read(incident_id=record.id) or []
    user = User(**body.get("user"))

    try:
        slack_web_client.chat_postEphemeral(
            channel=record.channel_id,
            user=user.id,
            text="Incident events.",
            blocks=BlockBuilder.events_list(incident=record, events=events),
        )
    except SlackApiError as error:
        logger.exception("error sending events list to slack", error=error)


@app.action("incident.delete_event")
def delete_incident_event(ack, body):
    ack()

    event_id = body.get("actions")[0].get("value")
    channel_id = body.get("channel").get("id")
    user = User(**body.get("user"))

    EventLogHandler.delete(id=event_id)

    try:
        slack_web_client.chat_postEphemeral(
            channel=channel_id,
            user=user.id,
            text="Event deleted.",
        )
    except SlackApiError as error:
        logger.exception("error sending event delete confirmation to slack", error=error)


@app.action("incident.add_event_modal")
def show_add_event_modal(ack, body, client):
    ack()

    channel_id = body.get("channel").get("id")

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "incident.add_event_modal",
            "private_metadata": channel_id,
            "title": {"type": "plain_text", "text": "Add Event"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "add_event_date",
                    "element": {
                        "type": "datepicker",
                        "action_id": "add_event_date",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Date"},
                },
                {
                    "type": "input",
                    "block_id": "add_event_time",
                    "element": {
                        "type": "timepicker",
                        "action_id": "add_event_time",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select time",
                        },
                    },
                    "label": {"type": "plain_text", "text": "Time"},
                },
                {
                    "type": "input",
                    "block_id": "add_event_text",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "add_event_text",
                    },
                    "label": {"type": "plain_text", "text": "Description"},
                },
            ],
        },
    )


@app.view("incident.add_event_modal")
def handle_add_event_submission(ack, body):
    ack()

    channel_id = body.get("view").get("private_metadata")
    parsed = parse_modal_values(body)
    user = User(**body.get("user"))

    event_date = parsed.get("add_event_date")
    event_time = parsed.get("add_event_time")
    event_text = parsed.get("add_event_text")
    ts = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")

    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)

    EventLogHandler.create(
        event=event_text,
        incident_id=record.id,
        incident_slug=record.slug,
        source="user",
        timestamp=ts,
        user=user.id,
    )

    try:
        slack_web_client.chat_postMessage(
            channel=record.channel_id,
            text=f"Timeline event added: {ts} — {event_text}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"> *{ts.strftime('%Y-%m-%d %H:%M')}* — {event_text} _(added by <@{user.id}>)_",
                    },
                }
            ],
        )
    except SlackApiError as error:
        logger.exception("error posting event confirmation to slack", error=error)




# Postmortem


def _postmortem_link_blocks(summary: str, postmortem_link: str) -> list[dict]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{summary}\n<{postmortem_link}|Open postmortem>",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View Postmortem"},
                    "style": "primary",
                    "url": postmortem_link,
                    "action_id": "view_postmortem",
                },
            ],
        },
    ]


# "incident.generate_postmortem" is the action_id of the "Generate Postmortem"
# button rendered in the resolution message (messages.py). Upstream never
# registered a handler for it, leaving the button dead. Wire it to the same
# generate-and-sync logic as the incident pane's "Postmortem" button.
@app.action("incident.generate_postmortem")
@app.action("incident.sync_or_create_postmortem")
def handle_sync_or_create_postmortem(ack, body):
    """
    Generate a postmortem if needed, then sync pinned content for Confluence.
    """
    ack()

    parsed_body = SlackBlockActionsResponse(**body)
    channel_id = parsed_body.channel.id
    user_id = parsed_body.user.id

    if not begin_postmortem_sync(channel_id):
        slack_web_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text="Postmortem sync is already in progress for this incident.",
        )
        return

    slack_web_client.chat_postEphemeral(
        channel=channel_id,
        user=user_id,
        text="Postmortem sync has started. This can take a minute.",
    )

    try:
        postmortem_link = asyncio.run(generate_postmortem(channel_id=channel_id))

        if not postmortem_link:
            slack_web_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="Unable to generate a postmortem for this incident. Check that the postmortem integration is configured correctly.",
            )
            return

        if _is_confluence_postmortem_link(postmortem_link):
            summary = "Postmortem is ready and pinned content has been synchronized."
            asyncio.run(sync_postmortem(channel_id=channel_id))
            slack_web_client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text=summary,
                blocks=_postmortem_link_blocks(summary, postmortem_link),
            )
            return

        summary = (
            "Postmortem is ready. Pinned-content sync is currently only "
            "supported for Confluence postmortems."
        )
        slack_web_client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=summary,
            blocks=_postmortem_link_blocks(summary, postmortem_link),
        )
    finally:
        end_postmortem_sync(channel_id)
