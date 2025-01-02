import asyncio

from incidentbot.configuration.settings import settings
from incidentbot.incident.actions import (
    set_severity as set_incident_severity,
    set_status as set_incident_status,
)
from incidentbot.logging import logger
from incidentbot.maintenance_window.actions import (
    set_status as set_maintenance_window_status,
)
from incidentbot.models.incident import IncidentDatabaseInterface
from incidentbot.models.maintenance_window import (
    MaintenanceWindowDatabaseInterface,
)
from incidentbot.models.slack import (
    CommandInvocation,
    SlackBlockActionsResponse,
    SlackViewSubmissionResponse,
    User,
)
from incidentbot.scheduler.core import process as TaskScheduler
from incidentbot.slack.client import slack_web_client
from incidentbot.slack.handler import app
from incidentbot.slack.messages import BlockBuilder
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
                logger.error(
                    f"error sending message back to user via slash command invocation: {error}"
                )
        case "maintenance":
            try:
                slack_web_client.chat_postEphemeral(
                    channel=command.channel_id,
                    user=command.user_id,
                    text="Options for managing maintenance windows.",
                    blocks=command_blocks(maintenance=True),
                )
            except SlackApiError as error:
                logger.error(
                    f"error sending message back to user via slash command invocation: {error}"
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
                    logger.error(
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
                    logger.error(
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
                logger.error(
                    f"error sending message back to user via slash command invocation: {error}"
                )


def command_blocks(
    maintenance: bool = False, root: bool = False, this: bool = False
) -> list[dict[str, Any]]:
    """
    Blocks for command input
    """

    join_buttons = [
        {
            "type": "button",
            "text": {
                "type": "plain_text",
                "text": "👤 Join as {}".format(
                    " ".join(role.split("_")).title()
                ),
                "emoji": True,
            },
            "value": f"join_this_incident_{role}",
            "action_id": f"incident.join_this_incident_{role}",
        }
        for role in [key for key, _ in settings.roles.items()]
    ]

    if maintenance:
        return [
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "List Maintenance Windows",
                            "emoji": True,
                        },
                        "value": "list_maintenance_windows",
                        "action_id": "maintenance_windows.list",
                        "style": "primary",
                    },
                ],
            }
        ]

    if root:
        return [
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
                            "text": "Manage Timelines",
                            "emoji": True,
                        },
                        "value": "show_incident_timeline_modal",
                        "action_id": "incident_timeline_modal",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Send Updates",
                            "emoji": True,
                        },
                        "value": "show_incident_update_modal",
                        "action_id": "incident_update_modal",
                    },
                ],
            }
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
                        "style": "primary",
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
                        "style": "primary",
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
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "List Responders",
                            "emoji": True,
                        },
                        "value": "this_incident_view_responders",
                        "action_id": "incident.view_responders",
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🛟 Get Help",
                            "emoji": True,
                        },
                        "value": "get_help_for_this_incident",
                        "action_id": "incident.get_help_for_this_incident",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📟 Page On-call",
                            "emoji": True,
                        },
                        "action_id": "pager",
                    },
                ]
                + join_buttons,
            }
        ]


"""
Command Modals and Actions
"""

"""
Incident Management
"""


# Describe


@app.action("incident.describe_this_incident")
def show_responders(ack, body):
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
        logger.error(f"error sending describe message to slack: {error}")


@app.action("maintenance_windows.list")
def list_maintenance_windows(ack, body):
    """
    Provides the response for listing maintenance windows
    """

    ack()

    channel_id = body.get("channel").get("id")
    records = MaintenanceWindowDatabaseInterface.list_all()
    user = User(**body.get("user"))

    try:
        slack_web_client.chat_postEphemeral(
            channel=channel_id,
            user=user.id,
            text="Maintenance windows list.",
            blocks=BlockBuilder.maintenance_window_list(
                maintenance_windows=records,
            ),
        )

        return
    except SlackApiError as error:
        logger.error(f"error sending describe message to slack: {error}")


# Severity


@app.action("incident.set_this_severity_modal")
def show_modal(ack, body, client):
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
def handle_submission(ack, body):  # noqa: F811
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
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


# Status


@app.action("incident.set_this_status_modal")
def show_modal(ack, body, client):  # noqa: F811
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
            "blocks": BlockBuilder.set_this_status_modal(
                object_type="incident", record=record
            ),
        },
    )


@app.view("incident.set_this_status_modal")
def handle_submission(ack, body):  # noqa: F811
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
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)


# Roles


@app.action("incident.view_responders")
def show_responders(ack, body):  # noqa: F811
    """
    Provides the response for viewing an incident's reponders
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
        logger.error(f"error sending responders list to slack: {error}")


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
            logger.error(f"error sending responders list to slack: {error}")
    else:
        try:
            slack_web_client.chat_postEphemeral(
                channel=record.channel_id,
                user=user.id,
                text="There are currently no tasks associated with this incident.",
            )

            return
        except SlackApiError as error:
            logger.error(f"error sending responders list to slack: {error}")


"""
Maintenance Windows
"""


@app.action("maintenance_window.set_this_status_modal")
def show_modal(ack, body, client):  # noqa: F811
    """
    Provides the modal that will display for setting a maintenance window's status
    """

    ack()

    parsed_body = SlackBlockActionsResponse(**body)
    maintenance_window_id = (
        parsed_body.actions[0].get("block_id").split("_")[-1:][0]
    )
    record = MaintenanceWindowDatabaseInterface.get_one(
        id=maintenance_window_id
    )

    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            "callback_id": "maintenance_window.set_this_status_modal",
            "title": {
                "type": "plain_text",
                "text": "Set status",
            },
            "submit": {"type": "plain_text", "text": "Done"},
            "blocks": BlockBuilder.set_this_status_modal(
                object_type="maintenance_window", record=record
            ),
        },
    )


@app.view("maintenance_window.set_this_status_modal")
def handle_submission(ack, body):  # noqa: F811
    """
    Handles maintenance_window.set_this_status_modal
    """

    ack()

    parsed_body = SlackViewSubmissionResponse(**body)
    new_status = (
        parsed_body.view.state.values.get(
            "set_this_status_modal_status_select"
        )
        .get("maintenance_window.set_this_status")
        .get("selected_option")
        .get("text")
        .get("text")
    )

    maintenance_window_id = (
        parsed_body.view.blocks[0].get("block_id").split("_")[-1:][0]
    )

    asyncio.run(
        set_maintenance_window_status(
            id=maintenance_window_id, status=new_status
        )
    )


@app.action("maintenance_window.set_this_status")
def handle_static_action(ack, body, logger):  # noqa: F811
    ack()
    logger.debug(body)
