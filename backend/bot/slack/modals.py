import config
import logging
import variables

from bot.audit.log import read as read_logs, write as write_log
from bot.exc import ConfigurationError
from bot.incident import incident
from bot.models.incident import (
    db_read_all_incidents,
    db_read_incident_channel_id,
    db_read_open_incidents,
    db_update_incident_last_update_sent_col,
)
from bot.models.pager import read_pager_auto_page_targets
from bot.shared import tools
from bot.slack.handler import app, help_menu
from bot.slack.messages import incident_list_message, pd_on_call_message
from bot.templates.incident.updates import (
    IncidentUpdate,
)
from datetime import datetime

logger = logging.getLogger("slack.modals")


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
        {"type": "divider"},
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
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":point_right: Some Handy Stuff You Should Know",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "- You can react to any message or image in any incident"
                + " channel with :pushpin: and I'll automatically add it to the RCA!",
            },
        },
        {"type": "divider"},
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
    # Also add in open incident info
    database_data = db_read_all_incidents()
    open_incidents = incident_list_message(database_data, all=False)
    base_blocks.extend(open_incidents)
    # On call info
    if "pagerduty" in config.active.integrations:
        from bot.pagerduty import api as pd_api

        pd_oncall_data = pd_api.find_who_is_on_call()
        on_call_info = pd_on_call_message(data=pd_oncall_data)
        base_blocks.extend(on_call_info)
    # Version info
    base_blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"If anyone asks, I'm running version {config.__version__}!",
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
                "action_id": "description",
                "placeholder": {
                    "type": "plain_text",
                    "text": "A brief description of the problem.",
                },
            },
            "label": {"type": "plain_text", "text": "Description"},
        },
    ]

    severities = []
    for sev, _ in config.active.severities.items():
        severities.append(
            {
                "text": {
                    "type": "plain_text",
                    "text": sev.upper(),
                    "emoji": True,
                },
                "value": sev,
            },
        )
    base_blocks.append(
        {
            "block_id": "severity",
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Severity*"},
            "accessory": {
                "type": "static_select",
                "action_id": "open_incident_modal_severity",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select a severity...",
                    "emoji": True,
                },
                "options": severities,
            },
        }
    ),
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
def handle_submission(ack, body, client, view):
    """
    Handles open_incident_modal
    """
    ack()
    is_security_incident = view["state"]["values"]["is_security_incident"][
        "open_incident_modal_set_security_type"
    ]["selected_option"]["value"]
    private_channel = view["state"]["values"]["private_channel"][
        "open_incident_modal_set_private"
    ]["selected_option"]["value"]
    description = view["state"]["values"]["open_incident_modal_desc"][
        "description"
    ]["value"]
    user = body["user"]["id"]
    severity = view["state"]["values"]["severity"][
        "open_incident_modal_severity"
    ]["selected_option"]["value"]
    # Create request parameters object
    try:
        request_parameters = incident.RequestParameters(
            channel="modal",
            incident_description=description,
            user=user,
            severity=severity,
            created_from_web=False,
            is_security_incident=is_security_incident
            in (
                "True",
                "true",
                True,
            ),
            private_channel=private_channel
            in (
                "True",
                "true",
                True,
            ),
        )
        resp = incident.create_incident(request_parameters)
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
    options = []
    logger.info(
        "Received request to open incident update modal, matched {} open incidents.".format(
            len(database_data)
        )
    )
    if len(database_data) == 0:
        options.append(
            {
                "text": {
                    "type": "plain_text",
                    "text": "None",
                    "emoji": True,
                },
                "value": "none",
            }
        )
        view = {
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_general_update_modal",
            "title": {"type": "plain_text", "text": "Provide incident update"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "There are currently no open incidents.",
                    },
                },
            ],
        }
    else:
        for inc in database_data:
            if inc.status != "resolved":
                options.append(
                    {
                        "text": {
                            "type": "plain_text",
                            "text": f"<#{inc.channel_id}>",
                            "emoji": True,
                        },
                        "value": f"<#{inc.channel_id}>",
                    },
                )
        view = {
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_general_update_modal",
            "title": {"type": "plain_text", "text": "Provide incident update"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
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
                        "options": options,
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
            ],
        }

    client.views_open(
        trigger_id=body["trigger_id"],
        view=view,
    )


@app.view("open_incident_general_update_modal")
def handle_submission(ack, client, view):
    """
    Handles open_incident_general_update_modal
    """
    ack()

    # Format message to be sent as an update
    channel_id = view["state"]["values"][
        "open_incident_general_update_modal_incident_channel"
    ]["incident_update_modal_select_incident"]["selected_option"]["value"]
    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")
    try:
        client.chat_postMessage(
            channel=variables.digest_channel_id,
            blocks=IncidentUpdate.public_update(
                incident_id=channel_id,
                impacted_resources=view["state"]["values"][
                    "open_incident_general_update_modal_impacted_resources"
                ]["impacted_resources"]["value"],
                message=view["state"]["values"][
                    "open_incident_general_update_modal_update_msg"
                ]["message"]["value"],
                timestamp=tools.fetch_timestamp(),
            ),
            text=view["state"]["values"][
                "open_incident_general_update_modal_update_msg"
            ]["message"]["value"],
        )
    except Exception as error:
        logger.error(f"Error sending update out for {channel_id}: {error}")
    finally:
        db_update_incident_last_update_sent_col(
            channel_id=channel_id,
            last_update_sent=tools.fetch_timestamp(),
        )


"""
Paging
"""


@app.shortcut("open_incident_bot_pager")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    if "pagerduty" in config.active.integrations:
        from bot.pagerduty import api as pd_api

        # Format incident list
        database_data = db_read_open_incidents()
        incident_options = []
        if len(database_data) == 0:
            incident_options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": "None",
                        "emoji": True,
                    },
                    "value": "none",
                }
            )
        else:
            for inc in database_data:
                if inc.status != "resolved":
                    incident_options.append(
                        {
                            "text": {
                                "type": "plain_text",
                                "text": inc.channel_name,
                                "emoji": True,
                            },
                            "value": f"{inc.channel_name}/{inc.channel_id}",
                        },
                    )
        # Call views_open with the built-in client
        client.views_open(
            # Pass a valid trigger_id within 3 seconds of receiving it
            trigger_id=body["trigger_id"],
            # View payload
            view={
                "type": "modal",
                "callback_id": "incident_bot_pager_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Page a team in PagerDuty",
                },
                "blocks": [
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
                                        "text": ep,
                                    },
                                    "value": ep,
                                }
                                for ep in pd_api.find_who_is_on_call()
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
                                        "text": "low",
                                    },
                                    "value": "low",
                                },
                                {
                                    "text": {
                                        "type": "plain_text",
                                        "text": "high",
                                    },
                                    "value": "high",
                                },
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
                            "options": incident_options,
                        },
                    },
                ],
            },
        )
    else:
        client.views_open(
            # Pass a valid trigger_id within 3 seconds of receiving it
            trigger_id=body["trigger_id"],
            # View payload
            view={
                "type": "modal",
                "callback_id": "incident_bot_pager_modal",
                "title": {
                    "type": "plain_text",
                    "text": "Page a team in PagerDuty",
                },
                "blocks": [
                    {
                        "type": "section",
                        "block_id": "incident_bot_pager_disabled",
                        "text": {
                            "type": "mrkdwn",
                            "text": "The PagerDuty integration is not currently enabled.",
                        },
                    },
                ],
            },
        )


@app.action("update_incident_bot_pager_selected_incident")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()

    team = body["view"]["state"]["values"]["incident_bot_pager_team_select"][
        "update_incident_bot_pager_selected_team"
    ]["selected_option"]["value"]

    priority = body["view"]["state"]["values"][
        "incident_bot_pager_priority_select"
    ]["update_incident_bot_pager_selected_priority"]["selected_option"][
        "value"
    ]

    incident_channel_name = body["view"]["state"]["values"][
        "incident_bot_pager_incident_select"
    ]["update_incident_bot_pager_selected_incident"]["selected_option"][
        "value"
    ].split(
        "/"
    )[
        0
    ]

    incident_channel_id = body["view"]["state"]["values"][
        "incident_bot_pager_incident_select"
    ]["update_incident_bot_pager_selected_incident"]["selected_option"][
        "value"
    ].split(
        "/"
    )[
        1
    ]

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
                "text": "Page a team in PagerDuty",
            },
            "submit": {"type": "plain_text", "text": "Page"},
            "blocks": [
                {
                    "type": "section",
                    "block_id": "incident_bot_pager_info",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*You have selected the following options - please review them carefully.*\n\n"
                        + "Once you click Submit, an incident will be created in PagerDuty for the team listed here and they will be paged. "
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
def handle_some_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_pager_selected_priority")
def handle_some_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("incident_bot_pager_modal")
def handle_submission(ack, body, say, view):
    """
    Handles open_incident_bot_pager
    """
    ack()
    logger.info("Attempting to page user...")
    from bot.pagerduty import api as pd_api

    team = view["blocks"][2]["block_id"].split("/")[1]
    priority = view["blocks"][3]["block_id"].split("/")[1]
    incident_channel_name = view["blocks"][4]["block_id"].split("/")[1]
    incident_channel_id = view["blocks"][4]["block_id"].split("/")[2]
    paging_user = body["user"]["name"]

    try:
        pd_api.page(
            ep_name=team,
            priority=priority,
            channel_name=incident_channel_name,
            channel_id=incident_channel_id,
            paging_user=paging_user,
        )
    except Exception as error:
        logger.error(error)
    finally:
        say(
            channel=incident_channel_id,
            text=f"*NOTICE:* I have paged the team/escalation policy '{team}' "
            + f"to respond to this incident via PagerDuty at the request of *{paging_user}*.",
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f":robot_face: PagerDuty Page Notification",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*NOTICE:* I have paged the team/escalation policy '{team}' to respond to this incident via PagerDuty at the request of *{paging_user}*.",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "image",
                            "image_url": "https://i.imgur.com/IVvdFCV.png",
                            "alt_text": "pagerduty",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"An corresponding PagerDuty incident has been created to notify the team to respond at: {tools.fetch_timestamp()}",
                        },
                    ],
                },
            ],
        )


"""
Timeline
"""


@app.shortcut("open_incident_bot_timeline")
def open_modal(ack, body, client):
    # Acknowledge the command request
    ack()

    # Format incident list
    database_data = db_read_open_incidents()
    incident_options = []
    for inc in database_data:
        if inc.status != "resolved":
            incident_options.append(
                {
                    "text": {
                        "type": "plain_text",
                        "text": inc.channel_name,
                        "emoji": True,
                    },
                    "value": f"{inc.channel_name}/{inc.channel_id}",
                },
            )
    base_blocks = []
    if len(incident_options) == 0:
        base_blocks.append(
            {
                "type": "section",
                "block_id": "no_incidents",
                "text": {
                    "type": "mrkdwn",
                    "text": "There are currently no open incidents.\n\nYou can only add timeline events to open incidents.",
                },
            },
        )
    else:
        base_blocks.extend(
            [
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
                        "options": incident_options,
                    },
                },
            ]
        )
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            "callback_id": "incident_bot_timeline_modal",
            "title": {"type": "plain_text", "text": "Incident timeline"},
            "blocks": base_blocks,
        },
    )


@app.action("update_incident_bot_timeline_selected_incident")
def update_modal(ack, body, client):
    # Acknowledge the button request
    ack()

    incident_channel_name = body["view"]["state"]["values"][
        "incident_bot_timeline_incident_select"
    ]["update_incident_bot_timeline_selected_incident"]["selected_option"][
        "value"
    ].split(
        "/"
    )[
        0
    ]

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
                + "be automatically added to the RCA when the incident is resolved.\n",
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
def handle_some_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_time")
def handle_some_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.action("update_incident_bot_timeline_text")
def handle_some_action(ack, body, logger):
    ack()
    logger.debug(body)


@app.view("incident_bot_timeline_modal_add")
def handle_submission(ack, body, say, view):
    """
    Handles
    """
    ack()

    incident_id = view["blocks"][0]["text"]["text"]
    event_date = view["state"]["values"]["date"][
        "update_incident_bot_timeline_date"
    ]["selected_date"]
    event_time = view["state"]["values"]["time"][
        "update_incident_bot_timeline_time"
    ]["selected_time"]
    event_text = view["state"]["values"]["text"][
        "update_incident_bot_timeline_text"
    ]["value"]
    ts = tools.fetch_timestamp_from_time_obj(
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
