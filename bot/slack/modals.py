import config
import logging

from .handler import app
from .handler import help_menu
from .client import return_slack_channel_info
from .messages import incident_list_message, pd_on_call_message
from bot.db import db
from bot.incident import incident
from bot.shared import tools

logger = logging.getLogger(__name__)


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
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Hi there, <@"
                + event["user"]
                + "> :wave:*!\n\nI'm your friendly Incident Bot, and my sole purpose is to help us identify and run incidents.",
            },
        },
        {"type": "divider"},
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":fast_forward: TLDR",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "To start a new incident, simply use the Slack search bar at the top of this window and search for my shortcut *_start a new incident_* - you'll know it's mine because you'll see my name next to it.\n\nAlternatively, you can mention me in any channel I'm in and say *_new <description>_*.",
            },
        },
        {
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "How to start a new incident ->",
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
                "text": ":point_right: My Commands",
            },
        },
        {"type": "divider"},
    ]
    help_block = help_menu(include_header=False)
    base_blocks.extend(help_block)
    # Also add in open incident info
    database_data = db.db_read_all_incidents()
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


@app.shortcut("open_incident_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to start an incident
    """
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view={
            "type": "modal",
            # View identifier
            "callback_id": "open_incident_modal",
            "title": {"type": "plain_text", "text": "Start a new incident"},
            "submit": {"type": "plain_text", "text": "Start"},
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This will start a new incident channel and you will be invited to it. From there, please use our incident management process to run the incident or coordinate with others to do so.",
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
            ],
        },
    )


@app.view("open_incident_modal")
def handle_submission(ack, body, client, view):
    """
    Handles open_incident_modal
    """
    ack()
    description = view["state"]["values"]["open_incident_modal_desc"]["description"][
        "value"
    ]
    user = body["user"]["id"]
    request_parameters = {
        "channel": "modal",
        "channel_description": description,
        "user": user,
        "created_from_web": False,
    }
    resp = incident.create_incident(request_parameters)
    client.chat_postMessage(channel=user, text=resp)


@app.shortcut("open_incident_general_update_modal")
def open_modal(ack, body, client):
    """
    Provides the modal that will display when the shortcut is used to update audience about an incident
    """
    ack()

    # Build blocks for open incidents
    database_data = db.db_read_open_incidents()
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
                        "text": "This will send a formatted, timestamped message to the public incidents channel to provide an update on the status of an incident. Use this to keep those outside the incident process informed.",
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
                    "label": {"type": "plain_text", "text": "Impacted Resources:"},
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
                    "label": {"type": "plain_text", "text": "Message to Include:"},
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
    # Get channel id of the incidents digest channel to send updates to
    channels = return_slack_channel_info()
    index = tools.find_index_in_list(channels, "name", config.incidents_digest_channel)
    digest_channel_id = channels[index]["id"]

    # Format message to be sent as an update
    channel_id = view["state"]["values"][
        "open_incident_general_update_modal_incident_channel"
    ]["incident_update_modal_select_incident"]["selected_option"]["value"]
    # Extract the channel ID without extra characters
    for character in "#<>":
        channel_id = channel_id.replace(character, "")
    try:
        update = incident.build_public_status_update(
            incident_id=channel_id,
            impacted_resources=view["state"]["values"][
                "open_incident_general_update_modal_impacted_resources"
            ]["impacted_resources"]["value"],
            message=view["state"]["values"][
                "open_incident_general_update_modal_update_msg"
            ]["message"]["value"],
        )
        client.chat_postMessage(channel=digest_channel_id, blocks=update, text="")
    except Exception as error:
        logger.error(f"Error sending update out for {channel_id}: {error}")
    finally:
        db.db_update_incident_last_update_sent_col(
            channel_id=channel_id,
            last_update_sent=tools.fetch_timestamp(),
        )
