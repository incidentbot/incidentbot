import config

from bot.audit.log import read as read_logs, write as write_log
from bot.exc import ConfigurationError
from bot.incident import incident
from bot.jira.issue import JiraIssue
from bot.models.incident import (
    db_read_incident_channel_id,
    db_read_open_incidents,
    db_read_recent_incidents,
    db_read_incident,
    db_update_incident_last_update_sent_col,
    db_update_jira_issues_col,
)
from bot.models.pager import read_pager_auto_page_targets
from bot.models.pg import OperationalData, Session
from bot.utils import utils
from bot.slack.client import check_user_in_group, get_digest_channel_id
from bot.slack.handler import app, help_menu
from bot.slack.messages import (
    incident_list_message,
)
from bot.statuspage.handler import (
    StatuspageComponents,
    StatuspageIncident,
    StatuspageIncidentUpdate,
)
from bot.templates.incident.updates import (
    IncidentUpdate,
)
from bot.templates.tools import parse_modal_values
from logger import logger
from datetime import datetime


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
    """
    Provide information via the app's home screen
    """
    base_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":robot_face: Incident Bot",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Start New Incident",
                        "emoji": True,
                    },
                    "value": "show_incident_modal",
                    "action_id": "open_incident_modal",
                    "style": "danger",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Hi there, <@"
                + event["user"]
                + "> :wave:*!\n\nI'm your friendly Incident Bot, and my "
                + "sole purpose is to help us identify and run incidents.\n",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":firefighter: Creating Incidents",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "To start a new incident, you can do the following:\n"
                + "- Use the button here\n "
                + "- Search for 'start a new incident' in the Slack search bar\n"
                + "- type _/start_ in any Slack channel to find my command and run it.",
            },
        },
        {
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "How to start a new incident",
                "emoji": True,
            },
            "image_url": "https://i.imgur.com/bGGtLr4.png",
            "alt_text": "how to start a new incident",
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: Documentation and Learning Materials",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "I have a lot of features. To check them all out, visit my <https://docs.incidentbot.io/|docs>.",
            },
        },
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: My Commands",
            },
        },
        {"type": "divider"},
    ]
    help_block = help_menu(include_header=False)
    base_blocks.extend(help_block)

    # Show truncated list of most recent incidents
    database_data = db_read_recent_incidents(
        limit=config.show_most_recent_incidents_app_home_limit
    )
    open_incidents = incident_list_message(database_data, all=False)
    base_blocks.extend(open_incidents)

    # Version info
    base_blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Version {config.__version__}",
                    }
                ],
            },
        ]
    )
    try:
        client.views_publish(
            user_id=event["user"],
            view={
                "type": "home",
                "blocks": base_blocks,
            },
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")


@app.action("open_incident_modal")
@app.shortcut("open_incident_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to start an incident
    """
    placeholder_severity = [
        sev for sev, _ in config.active.severities.items()
    ][-1]

    base_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This will start a new incident channel and you will "
                + "be invited to it. From there, please use our incident "
                + "management process to run the incident or coordinate "
                + "with others to do so.",
            },
        },
        {
            "type": "section",
            "block_id": "is_security_incident",
            "text": {
                "type": "mrkdwn",
                "text": "*Is this a security incident?*",
            },
            "accessory": {
                "action_id": "open_incident_modal_set_security_type",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        },
        {
            "type": "section",
            "block_id": "private_channel",
            "text": {
                "type": "mrkdwn",
                "text": "*Make Slack channel private?*",
            },
            "accessory": {
                "action_id": "open_incident_modal_set_private",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select...",
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": "No",
                    },
                    "value": "false",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Yes",
                        },
                        "value": "true",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "No",
                        },
                        "value": "false",
                    },
                ],
            },
        },
        {
            "type": "input",
            "block_id": "open_incident_modal_desc",
            "element": {
                "type": "plain_text_input",
                "action_id": "open_incident_modal_set_description",
                "placeholder": {
                    "type": "plain_text",
                    "text": "A brief description of the problem.",
                },
            },
            "label": {"type": "plain_text", "text": "Description"},
        },
        {
            "block_id": "severity",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Severity*"},
            "accessory": {
                "type": "static_select",
                "action_id": "open_incident_modal_set_severity",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a severity...",
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": placeholder_severity.upper(),
                    },
                    "value": placeholder_severity,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": sev.upper(),
                            "emoji": True,
                        },
                        "value": sev,
                    }
                    for sev, _ in config.active.severities.items()
                ],
            },
        },
    ]

    """
    If there are teams that will be auto paged, mention that
    """
    if "pagerduty" in config.active.integrations:
        auto_page_targets = read_pager_auto_page_targets()
        if len(auto_page_targets) != 0:
            base_blocks.extend(
                [
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": ":point_right: *The following teams will "
                            + "be automatically paged when this incident is created:*",
                        },
                    },
                ]
            )
            for i in auto_page_targets:
                for k, v in i.items():
                    base_blocks.extend(
                        [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": f"_{k}_",
                                },
                            },
                        ]
                    )
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_modal",
            "title": {"type": "plain_text", "text": "Start a new incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": base_blocks,
        },
    )


@app.view("open_incident_modal")
def handle_submission(ack, body, client):
    """
    Handles open_incident_modal
    """
    ack()
    parsed = parse_modal_values(body)
    user = body.get("user").get("id")

    # Create request parameters object
    try:
        resp = incident.create_incident(
            incident.RequestParameters(
                channel="modal",
                incident_description=parsed.get(
                    "open_incident_modal_set_description"
                ),
                user=user,
                severity=parsed.get("open_incident_modal_set_severity"),
                created_from_web=False,
                is_security_incident=parsed.get(
                    "open_incident_modal_set_security_type"
                )
                in (
                    "True",
                    "true",
                    True,
                ),
                private_channel=parsed.get("open_incident_modal_set_private")
                in (
                    "True",
                    "true",
                    True,
                ),
            )
        )
        client.chat_postMessage(channel=user, text=resp)
    except ConfigurationError as error:
        logger.error(error)


@app.action("open_incident_general_update_modal")
@app.shortcut("open_incident_general_update_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update audience about an incident
    """
    ack()

    # Build blocks for open incidents
    database_data = db_read_open_incidents()
    view = {
        "type": "modal",
        # View identifier
        "callback_id": "open_incident_general_update_modal",
        "title": {"type": "plain_text", "text": "Provide incident update"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "blocks": (
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This will send a formatted, timestamped message "
                        + "to the public incidents channel to provide an update "
                        + "on the status of an incident. Use this to keep those "
                        + "outside the incident process informed.",
                    },
                },
                {
                    "block_id": "open_incident_general_update_modal_incident_channel",
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "Associated Incident:",
                    },
                    "accessory": {
                        "type": "static_select",
                        "action_id": "incident_update_modal_select_incident",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select an ongoing incident...",
                            "emoji": True,
                        },
                        "options": [
                            (
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "None",
                                        "emoji": True,
                                    },
                                    "value": "none",
                                }
                                if len(database_data) == 0
                                else {
                                    "text": {
                                        "type": "plain_text",
                                        "text": f"<#{inc.channel_id}>",
                                        "emoji": True,
                                    },
                                    "value": f"<#{inc.channel_id}>",
                                }
                            )
                            for inc in database_data
                            if inc.status != "resolved"
                        ],
                    },
                },
                {
                    "type": "input",
                    "block_id": "open_incident_general_update_modal_impacted_resources",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "impacted_resources",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "e.g. API, Authentication, Dashboards",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Impacted Resources:",
                    },
                },
                {
                    "type": "input",
                    "block_id": "open_incident_general_update_modal_update_msg",
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "message",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "A brief message to include with this update.",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Message to Include:",
                    },
                },
            ]
            if len(database_data) != 0
            else [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "There are currently no open incidents.",
                    },
                },
            ]
        ),
    }
    client.views_open(
        trigger_id=body["trigger_id"],
        view=view,
    )


@app.view("open_incident_general_update_modal")
def handle_submission(ack, body, client):
    """
    Handles open_incident_general_update_modal
    """
    ack()

    # Get values from modal submission
    parsed = parse_modal_values(body)
    channel_id = parsed.get("incident_update_modal_select_incident")
    user_id = body.get("user").get("id")

    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")

    # We need the ts for the digest message so this will be a thread
    inc = db_read_incident(channel_id=channel_id)

    try:
        client.chat_postMessage(
            channel=get_digest_channel_id(),
            thread_ts=inc.dig_message_ts,
            blocks=IncidentUpdate.public_update(
                incident_id=channel_id,
                impacted_resources=parsed.get("impacted_resources"),
                message=parsed.get("message"),
                timestamp=utils.fetch_timestamp(),
                user_id=user_id,
            ),
            text="Incident update for incident <#{}>: {}".format(
                channel_id, parsed.get("message")
            ),
        )
    except Exception as error:
        logger.error(f"Error sending update out for {channel_id}: {error}")
    finally:
        db_update_incident_last_update_sent_col(
            channel_id=channel_id,
            last_update_sent=utils.fetch_timestamp(),
        )


"""
Paging
"""


@app.shortcut("open_incident_bot_pager")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    if "pagerduty" in config.active.integrations:
        from bot.pagerduty.api import image_url

        platform = "PagerDuty"
        oncalls = (
            Session.query(OperationalData)
            .filter(OperationalData.id == "pagerduty_oc_data")
            .one()
            .serialize()
            .get("json_data")
        )
        priorities = ["low", "high"]
        image_url = image_url
    elif "opsgenie" in config.active.integrations.get("atlassian"):
        from bot.opsgenie import api as og_api

        platform = "Opsgenie"
        sess = og_api.OpsgenieAPI()
        oncalls = sess.list_teams()
        priorities = sess.priorities
        image_url = og_api.image_url

    blocks = [
        {
            "type": "context",
            "elements": [
                {
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": "pagerduty",
                },
            ],
        },
        {
            "type": "section",
            "block_id": "incident_bot_pager_team_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose a team to page:",
            },
            "accessory": {
                "action_id": "update_incident_bot_pager_selected_team",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Team...",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": i,
                        },
                        "value": i,
                    }
                    for i in oncalls
                ],
            },
        },
        {
            "type": "section",
            "block_id": "incident_bot_pager_priority_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an urgency:",
            },
            "accessory": {
                "action_id": "update_incident_bot_pager_selected_priority",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Urgency...",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": i,
                        },
                        "value": i,
                    }
                    for i in priorities
                ],
            },
        },
        {
            "type": "section",
            "block_id": "incident_bot_pager_incident_select",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an incident:",
            },
            "accessory": {
                "action_id": "update_incident_bot_pager_selected_incident",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Incident...",
                },
                "options": [
                    (
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "None",
                                "emoji": True,
                            },
                            "value": "none",
                        }
                        if len(db_read_open_incidents()) == 0
                        else {
                            "text": {
                                "type": "plain_text",
                                "text": inc.channel_name,
                                "emoji": True,
                            },
                            "value": f"{inc.channel_name}/{inc.channel_id}",
                        }
                    )
                    for inc in db_read_open_incidents()
                    if inc.status != "resolved"
                ],
            },
        },
    ]
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_bot_pager_modal",
            "title": {
                "type": "plain_text",
                "text": f"Page a team in {platform}",
            },
            "blocks": (
                blocks
                if "pagerduty" in config.active.integrations
                or "opsgenie" in config.active.integrations.get("atlassian")
                else [
                    {
                        "type": "section",
                        "block_id": "incident_bot_pager_disabled",
                        "text": {
                            "type": "mrkdwn",
                            "text": "No pager integrations are enabled.",
                        },
                    },
                ]
            ),
        },
    )


@app.action("update_incident_bot_pager_selected_incident")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_incident_bot_pager_selected_incident")
    incident_channel_name = incident.split("/")[0]
    incident_channel_id = incident.split("/")[1]
    priority = parsed.get("update_incident_bot_pager_selected_priority")
    team = parsed.get("update_incident_bot_pager_selected_team")

    if "pagerduty" in config.active.integrations:
        platform = "PagerDuty"
        artifact = "incident"
    elif "opsgenie" in config.active.integrations.get("atlassian"):
        platform = "Opsgenie"
        artifact = "alert"

    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "incident_bot_pager_modal",
            "title": {
                "type": "plain_text",
                "text": f"Page a team in {platform}",
            },
            "submit": {"type": "plain_text", "text": "Page"},
            "blocks": [
                {
                    "type": "section",
                    "block_id": "incident_bot_pager_info",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*You have selected the following options - please review them carefully.*\n\n"
                        + f"Once you click Submit, an {artifact} will be created in {platform} for the team listed here and they will be paged. "
                        + "They will also be invited to the incident's Slack channel.",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "block_id": f"team/{team}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Team:* _{team}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"priority/{priority}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Urgency:* _{priority}_",
                    },
                },
                {
                    "type": "section",
                    "block_id": f"incident/{incident_channel_name}/{incident_channel_id}",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Incident:* _{incident_channel_name}_",
                    },
                },
            ],
        },
    )


@app.action("update_incident_bot_pager_selected_team")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_pager_selected_priority")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("incident_bot_pager_modal")
def handle_submission(ack, body, say, view):
    """
    Handles open_incident_bot_pager
    """
    ack()

    team = view["blocks"][2]["block_id"].split("/")[1]
    priority = view["blocks"][3]["block_id"].split("/")[1]
    incident_channel_name = view["blocks"][4]["block_id"].split("/")[1]
    incident_channel_id = view["blocks"][4]["block_id"].split("/")[2]
    paging_user = body["user"]["name"]

    if "pagerduty" in config.active.integrations:
        from bot.pagerduty.api import PagerDutyInterface

        pagerduty_interface = PagerDutyInterface(escalation_policy=team)

        platform = "PagerDuty"
        artifact = "incident"
    elif "opsgenie" in config.active.integrations.get("atlassian"):
        from bot.opsgenie import api as og_api

        platform = "Opsgenie"
        artifact = "alert"

    try:
        match platform.lower():
            case "pagerduty":
                pagerduty_interface.page(
                    priority=priority,
                    channel_name=incident_channel_name,
                    channel_id=incident_channel_id,
                    paging_user=paging_user,
                )
                msg = f"*NOTICE:* I have paged '{team}' to respond to this {artifact} via {platform} at the request of *{paging_user}*."
            case "opsgenie":
                sess = og_api.OpsgenieAPI()
                sess.create_alert(
                    channel_name=incident_channel_name,
                    channel_id=incident_channel_id,
                    paging_user=paging_user,
                    priority=priority,
                    responders=[team],
                )
                msg = f"*NOTICE:* I have paged '{team}' to respond to this {artifact} via {platform} at the request of *{paging_user}*."
    except Exception as error:
        msg = f"Looks like I encountered an error issuing that page: {error}"
    finally:
        say(
            channel=incident_channel_id,
            text=msg,
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":robot_face: {platform} Page Notification",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": msg,
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"This {platform} action was attempted at: {utils.fetch_timestamp()}",
                        },
                    ],
                },
            ],
        )


"""
Timeline
"""


@app.action("open_incident_bot_timeline")
@app.shortcut("open_incident_bot_timeline")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    # Format incident list
    database_data = db_read_open_incidents()

    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "blocks": [
                (
                    {
                        "type": "section",
                        "block_id": "incident_bot_timeline_incident_select",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Choose an incident to add an event to:",
                        },
                        "accessory": {
                            "action_id": "update_incident_bot_timeline_selected_incident",
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Incident...",
                            },
                            "options": [
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": inc.channel_name,
                                        "emoji": True,
                                    },
                                    "value": f"{inc.channel_name}/{inc.channel_id}",
                                }
                                for inc in database_data
                                if inc.status != "resolved"
                            ],
                        },
                    }
                    if len(database_data) != 0
                    else {
                        "type": "section",
                        "block_id": "no_incidents",
                        "text": {
                            "type": "mrkdwn",
                            "text": "There are currently no open incidents.\n\nYou can only add timeline events to open incidents.",
                        },
                    }
                )
            ],
        },
    )


@app.action("update_incident_bot_timeline_selected_incident")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()

    parsed = parse_modal_values(body)
    incident = parsed.get("update_incident_bot_timeline_selected_incident")
    incident_channel_name = incident.split("/")[0]
    current_logs = read_logs(incident_channel_name)
    base_blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": incident_channel_name,
            },
        },
        {
            "type": "section",
            "block_id": "incident_bot_timeline_info",
            "text": {
                "type": "mrkdwn",
                "text": "Add a new event to the incident's timeline. This will "
                + "be automatically added to the postmortem when the incident is resolved.\n",
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":page_with_curl: Existing Entries",
            },
        },
    ]
    for log in current_logs:
        base_blocks.extend(
            [
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "plain_text",
                            "text": log["ts"],
                            "emoji": True,
                        }
                    ],
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": log["log"],
                    },
                },
                {"type": "divider"},
            ],
        )
    base_blocks.extend(
        [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":writing_hand: Add New",
                },
            },
            {
                "type": "input",
                "block_id": "date",
                "element": {
                    "type": "datepicker",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a date",
                        "emoji": True,
                    },
                    "action_id": "update_incident_bot_timeline_date",
                },
                "label": {"type": "plain_text", "text": "Date", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "time",
                "element": {
                    "type": "timepicker",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True,
                    },
                    "action_id": "update_incident_bot_timeline_time",
                },
                "label": {"type": "plain_text", "text": "Time", "emoji": True},
            },
            {
                "type": "input",
                "block_id": "text",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "update_incident_bot_timeline_text",
                },
                "label": {"type": "plain_text", "text": "Text", "emoji": True},
            },
        ]
    )

    # Call views_update with the built-in client
    client.views_update(
        # Pass the view_id
        view_id=body["view"]["id"],
        # String that represents view state to protect against race conditions
        hash=body["view"]["hash"],
        # View payload with updated blocks
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal_add",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "submit": {"type": "plain_text", "text": "Add"},
            "blocks": base_blocks,
        },
    )


@app.action("update_incident_bot_timeline_date")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_time")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_text")
def handle_static_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("incident_bot_timeline_modal_add")
def handle_submission(ack, body, say, view):
    """
    Handles
    """
    ack()

    parsed = parse_modal_values(body)
    incident_id = view["blocks"][0]["text"]["text"]
    event_date = parsed.get("update_incident_bot_timeline_date")
    event_time = parsed.get("update_incident_bot_timeline_time")
    event_text = parsed.get("update_incident_bot_timeline_text")
    ts = utils.fetch_timestamp_from_time_obj(
        datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
    )
    try:
        write_log(
            incident_id=incident_id,
            event=event_text,
            user=body["user"]["id"],
            ts=ts,
        )
    except Exception as error:
        logger.error(error)
    finally:
        say(
            channel=db_read_incident_channel_id(incident_id=incident_id),
            text=f":wave: *I have added the following event to this incident's timeline:* {ts} - {event_text}",
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f":wave: *I have added the following event to this incident's timeline:*",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{ts} - {event_text}",
                    },
                },
            ],
        )


"""
Statuspage
"""


@app.action("open_statuspage_incident_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to start a Statuspage incident
    """
    user = body.get("user").get("id")
    incident_id = body.get("actions")[0].get("value").split("_")[-1:][0]
    incident_data = db_read_incident(channel_id=incident_id)
    blocks = [
        {
            "type": "image",
            "image_url": config.sp_logo_url,
            "alt_text": "statuspage",
        },
        {"type": "divider"},
        {
            "type": "section",
            "block_id": incident_id,
            "text": {
                "type": "mrkdwn",
                "text": "Incident ID: {}".format(incident_data.incident_id),
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This Statuspage incident will start in "
                + "*investigating* mode. You may change its status as the "
                + "incident proceeds.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please enter a brief description that will appear "
                + "as the incident description in the Statuspage incident. "
                + "Then select impacted components and confirm. Once "
                + "confirmed, the incident will be opened.",
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "statuspage_name_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.name_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Name for the incident",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "statuspage_body_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.body_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message describing the incident",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_impact_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.impact_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an impact...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Minor",
                            "emoji": True,
                        },
                        "value": "minor",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major",
                            "emoji": True,
                        },
                        "value": "major",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Critical",
                            "emoji": True,
                        },
                        "value": "critical",
                    },
                ],
            },
        },
        {
            "block_id": "statuspage_components_status",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Components Impact:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.components_status_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select status of components...",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Degraded Performance",
                            "emoji": True,
                        },
                        "value": "degraded_performance",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Partial Outage",
                            "emoji": True,
                        },
                        "value": "partial_outage",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Major Outage",
                            "emoji": True,
                        },
                        "value": "major_outage",
                    },
                ],
            },
        },
        {
            "type": "section",
            "block_id": "statuspage_components_select",
            "text": {
                "type": "mrkdwn",
                "text": "Select impacted components",
            },
            "accessory": {
                "action_id": "statuspage.components_select",
                "type": "multi_static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select components",
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": c,
                        },
                        "value": c,
                    }
                    for c in StatuspageComponents().list_of_names
                ],
            },
        },
    ]

    ack()

    # Return modal only if user has permissions
    sp_config = config.active.integrations.get("statuspage")
    if sp_config.get("permissions") and sp_config.get("permissions").get(
        "groups"
    ):
        for gr in sp_config.get("permissions").get("groups"):
            if check_user_in_group(user_id=user, group_name=gr):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        # View identifier
                        "callback_id": "open_statuspage_incident_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Statuspage Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Start"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=incident_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                # View identifier
                "callback_id": "open_statuspage_incident_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Statuspage Incident",
                },
                "submit": {"type": "plain_text", "text": "Start"},
                "blocks": blocks,
            },
        )


@app.view("open_statuspage_incident_modal")
def handle_submission(ack, body, client, view):
    """
    Handles open_statuspage_incident_modal
    """
    ack()
    incident_data = db_read_incident(
        channel_id=view["blocks"][2].get("block_id")
    )

    # Fetch parameters from modal
    parsed = parse_modal_values(body)
    body = parsed.get("statuspage.body_input")
    impact = parsed.get("statuspage.impact_select")
    name = parsed.get("statuspage.name_input")
    status = parsed.get("statuspage.components_status_select")
    selected_components = parsed.get("statuspage.components_select")

    # Create Statuspage incident
    try:
        StatuspageIncident(
            channel_id=incident_data.channel_id,
            request_data={
                "name": name,
                "status": "investigating",
                "body": body,
                "impact": impact,
                "components": StatuspageComponents().formatted_components_update(
                    selected_components, status
                ),
            },
        )
    except Exception as error:
        logger.error(f"Error creating Statuspage incident: {error}")

    client.chat_update(
        channel=incident_data.channel_id,
        ts=incident_data.sp_message_ts,
        text="Statuspage incident has been created.",
        blocks=StatuspageIncidentUpdate.update_management_message(
            incident_data.channel_id
        ),
    )


@app.action("open_statuspage_incident_update_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update a Statuspage incident
    """
    user = body.get("user").get("id")
    incident_id = body.get("channel").get("id")
    incident_data = db_read_incident(channel_id=incident_id)
    sp_incident_data = incident_data.sp_incident_data
    blocks = [
        {"type": "divider"},
        {
            "type": "image",
            "image_url": config.sp_logo_url,
            "alt_text": "statuspage",
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Name*: {}\n*Status*: {}\nLast Updated: {}\n".format(
                    sp_incident_data.get("name"),
                    sp_incident_data.get("status"),
                    sp_incident_data.get("updated_at"),
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": f"statuspage_update_message_input_{incident_id}",
            "element": {
                "type": "plain_text_input",
                "action_id": "statuspage.update_message_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Message to include with this update",
                "emoji": True,
            },
        },
        {
            "block_id": "statuspage_incident_status_management",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Update Status:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "statuspage.update_status",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Investigating",
                    "emoji": True,
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Investigating",
                            "emoji": True,
                        },
                        "value": "investigating",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Identified",
                            "emoji": True,
                        },
                        "value": "identified",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Monitoring",
                            "emoji": True,
                        },
                        "value": "monitoring",
                    },
                    {
                        "text": {
                            "type": "plain_text",
                            "text": "Resolved",
                            "emoji": True,
                        },
                        "value": "resolved",
                    },
                ],
            },
        },
    ]

    ack()

    # Return modal only if user has permissions
    sp_config = config.active.integrations.get("statuspage")
    if sp_config.get("permissions") and sp_config.get("permissions").get(
        "groups"
    ):
        for gr in sp_config.get("permissions").get("groups"):
            if check_user_in_group(user_id=user, group_name=gr):
                client.views_open(
                    trigger_id=body["trigger_id"],
                    view={
                        "type": "modal",
                        # View identifier
                        "callback_id": "open_statuspage_incident_update_modal",
                        "title": {
                            "type": "plain_text",
                            "text": "Update Incident",
                        },
                        "submit": {"type": "plain_text", "text": "Update"},
                        "blocks": blocks,
                    },
                )
            else:
                client.chat_postEphemeral(
                    channel=incident_id,
                    user=user,
                    text="You don't have permissions to manage Statuspage incidents.",
                )
    else:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                # View identifier
                "callback_id": "open_statuspage_incident_update_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Update Incident",
                },
                "submit": {"type": "plain_text", "text": "Update"},
                "blocks": blocks,
            },
        )


@app.view("open_statuspage_incident_update_modal")
def handle_submission(ack, body):
    """
    Handles open_statuspage_incident_update_modal
    """
    ack()

    channel_id = (
        body.get("view").get("blocks")[4].get("block_id").split("_")[-1:][0]
    )
    values = body.get("view").get("state").get("values")
    update_message = (
        values.get(f"statuspage_update_message_input_{channel_id}")
        .get("statuspage.update_message_input")
        .get("value")
    )
    update_status = (
        values.get("statuspage_incident_status_management")
        .get("statuspage.update_status")
        .get("selected_option")
        .get("value")
    )

    try:
        StatuspageIncidentUpdate().update(
            channel_id, update_status, update_message
        )
    except Exception as error:
        logger.error(f"Error updating Statuspage incident: {error}")


"""
Jira
"""


@app.action("open_incident_create_jira_issue_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to create a Jira issue
    """
    incident_id = body.get("channel").get("id")
    from bot.jira.api import JiraApi

    j = JiraApi()

    blocks = [
        {
            "type": "header",
            "block_id": incident_id,
            "text": {
                "type": "plain_text",
                "text": "Create a Jira Issue",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "This issue will be created in the project: *{}*".format(
                    config.active.integrations.get("atlassian")
                    .get("jira")
                    .get("project")
                ),
            },
        },
        {"type": "divider"},
        {
            "type": "input",
            "block_id": "jira_issue_summary_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.summary_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Summary",
                "emoji": True,
            },
        },
        {
            "type": "input",
            "block_id": "jira_issue_description_input",
            "element": {
                "type": "plain_text_input",
                "action_id": "jira.description_input",
                "min_length": 1,
            },
            "label": {
                "type": "plain_text",
                "text": "Issue Description",
                "emoji": True,
            },
        },
        {
            "block_id": "jira_issue_type_select",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Issue Type:*"},
            "accessory": {
                "type": "static_select",
                "action_id": "jira.type_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": j.issue_types[0],
                    "emoji": True,
                },
                "initial_option": {
                    "text": {
                        "type": "plain_text",
                        "text": j.issue_types[0],
                    },
                    "value": j.issue_types[0],
                },
                "options": [
                    {
                        "text": {
                            "type": "plain_text",
                            "text": issue_type,
                            "emoji": True,
                        },
                        "value": issue_type,
                    }
                    for issue_type in j.issue_types
                ],
            },
        },
        # {
        #     "block_id": "jira_issue_priority_select",
        #     "type": "section",
        #     "text": {"type": "mrkdwn", "text": "*Priority:*"},
        #     "accessory": {
        #         "type": "static_select",
        #         "action_id": "jira.priority_select",
        #         "placeholder": {
        #             "type": "plain_text",
        #             "text": j.priorities[0],
        #             "emoji": True,
        #         },
        #         "initial_option": {
        #             "text": {
        #                 "type": "plain_text",
        #                 "text": j.priorities[0],
        #             },
        #             "value": j.priorities[0],
        #         },
        #         "options": [
        #             {
        #                 "text": {
        #                     "type": "plain_text",
        #                     "text": priority,
        #                     "emoji": True,
        #                 },
        #                 "value": priority,
        #             }
        #             for priority in j.priorities
        #         ],
        #     },
        # },
    ]

    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_create_jira_issue_modal",
            "title": {
                "type": "plain_text",
                "text": "Jira Issue",
            },
            "submit": {"type": "plain_text", "text": "Create"},
            "blocks": blocks,
        },
    )


@app.view("open_incident_create_jira_issue_modal")
def handle_submission(ack, body, client, view):
    """
    Handles open_incident_create_jira_issue_modal
    """
    ack()
    channel_id = body.get("view").get("blocks")[0].get("block_id")
    parsed = parse_modal_values(body)

    try:
        incident_data = db_read_incident(channel_id=channel_id)

        issue_obj = JiraIssue(
            incident_id=incident_data.incident_id,
            description=parsed.get("jira.description_input"),
            issue_type=parsed.get("jira.type_select"),
            # priority=parsed.get("jira.priority_select"),
            summary=parsed.get("jira.summary_input"),
        )

        resp = issue_obj.new()

        if resp is not None:
            issue_link = "{}/browse/{}".format(
                config.atlassian_api_url, resp.get("key")
            )
            db_update_jira_issues_col(
                channel_id=channel_id, issue_link=issue_link
            )
            try:
                from bot.slack.messages import new_jira_message

                resp = client.chat_postMessage(
                    channel=channel_id,
                    blocks=new_jira_message(
                        key=resp.get("key"),
                        summary=parsed.get("jira.summary_input"),
                        type=parsed.get("jira.type_select"),
                        link=issue_link,
                    ),
                    text="A Jira issue has been created for this incident: {}".format(
                        resp.get("self")
                    ),
                )
                client.pins_add(
                    channel=resp.get("channel"),
                    timestamp=resp.get("ts"),
                )
            except Exception as error:
                logger.error(
                    f"Error sending Jira issue message for {incident_data.incident_id}: {error}"
                )
        else:
            resp = client.chat_postMessage(
                channel=channel_id,
                text="Hmmm.. that didn't work. Check my logs for more information.",
            )
    except Exception as error:
        logger.error(error)
