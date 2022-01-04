import logging
import os
from typing import Dict, List, Tuple
import pyjokes

from __main__ import app, __version__
from ..core import slack_tools
from ..db import db
from ..statuspage import statuspage
from datetime import datetime
from slackeventsapi import SlackEventAdapter

logger = logging.getLogger(__name__)

# Initialize Slack Web API client
slack_events_adapter = SlackEventAdapter(
    os.getenv("SLACK_SIGNING_SECRET"), "/slack/events", server=app
)

# Error events
@slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))


# Example responder to bot mentions
@slack_events_adapter.on("app_mention")
def handle_mentions(event_data):
    event = event_data["event"]
    # Remove the bot's user ID from the mention to parse only the text
    message = str.split(event["text"], " ")[1:]
    # React to the following messages
    if "help" in message:
        if len(message) > 1:
            pass
        else:
            channel = event["channel"]
            resp = return_help(channel)
            slack_tools.slack_web_client.chat_postMessage(**resp)
    elif "lsoi" in message:
        channel = event["channel"]
        database_data = db.db_read_all_incidents()
        resp = format_incident_list_message(channel, database_data, all=False)
        slack_tools.slack_web_client.chat_postMessage(**resp)
    elif "lsai" in message:
        channel = event["channel"]
        database_data = db.db_read_all_incidents()
        resp = format_incident_list_message(channel, database_data, all=True)
        slack_tools.slack_web_client.chat_postMessage(**resp)
    elif "ls spinc" in " ".join(message):
        channel = event["channel"]
        if os.getenv("INCIDENT_EXTERNAL_PROVIDERS_ENABLED") != "true":
            sp_objects = statuspage.StatuspageObjects()
            sp_incidents = sp_objects.open_incidents
            resp = format_sp_incident_list_message(channel, sp_incidents)
            slack_tools.slack_web_client.chat_postMessage(**resp)
        else:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"The Statuspage integration is not enabled. I cannot provide information from Statuspage as a result.",
                        },
                    },
                ],
            )
    elif "tell me a joke" in " ".join(message):
        channel = event["channel"]
        resp = pyjokes.get_joke()
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel,
            text=resp,
        )
    elif "ping" in message:
        channel = event["channel"]
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel,
            text="pong",
        )
    elif "version" in message:
        channel = event["channel"]
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel,
            text=f"I am currently running version: {__version__}",
        )
    else:
        channel = event["channel"]
        requested = " ".join(message)
        slack_tools.slack_web_client.chat_postMessage(
            channel=channel,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Sorry, I don't know the command *{requested}* yet.",
                    },
                },
            ],
        )


## React
# @slack_tools.slack_events_adapter.on("reaction_added")
# def reaction_added(event_data):
#    event = event_data["event"]
#    emoji = event["reaction"]
#    channel = event["item"]["channel"]
#    text = ":%s:" % emoji
#    slack_tools.slack_web_client.chat_postMessage(channel=channel, text=text)


def format_incident_list_message(
    channel_id: str, incidents: List[Tuple], all: bool = False
) -> Dict[str, str]:
    """
    Format the response to show open incidents
    """
    base_block = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": ":open_file_folder: Open Incidents"},
        },
        {"type": "divider"},
    ]
    formatted_incidents = []
    none_found_block = {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":open_file_folder: No Open Incidents",
                },
            },
            {"type": "divider"},
        ],
    }
    # Check to see if there are any incidents
    if len(incidents) == 0:
        return none_found_block
    else:
        for inc in incidents:
            channel_id_int = inc[1]
            status = inc[3]
            severity = inc[4]
            if all == True:
                formatted_incidents.append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*ID:* <#{channel_id_int}>",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Severity:* {severity.upper()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:* {status.title()}",
                            },
                        ],
                    }
                )
                formatted_incidents.append({"type": "divider"})
            elif all == False:
                if status != "resolved":
                    formatted_incidents.append(
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*ID:* <#{channel_id_int}>",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Severity:* {severity.upper()}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Status:* {status.title()}",
                                },
                            ],
                        }
                    )
                    formatted_incidents.append({"type": "divider"})
    if len(formatted_incidents) == 0:
        return none_found_block
    else:
        for inc in formatted_incidents:
            base_block.append(inc)
        return {
            "channel": channel_id,
            "blocks": base_block,
        }


def format_sp_incident_list_message(
    channel_id: str, incidents: List[Dict[str, str]]
) -> Dict[str, str]:
    """
    Format the response to show open Statuspage ncidents
    """
    base_block = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": ":open_file_folder: Open Statuspage Incidents",
            },
        },
        {"type": "divider"},
    ]
    formatted_incidents = []
    none_found_block = {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":open_file_folder: No Open Statuspage Incidents",
                },
            },
            {"type": "divider"},
        ],
    }
    # Check to see if there are any incidents
    if len(incidents) == 0:
        return none_found_block
    else:
        for inc in incidents:
            name = inc["name"]
            status = inc["status"]
            impact = inc["impact"]
            created_at = inc["created_at"]
            updated_at = inc["updated_at"]
            shortlink = inc["shortlink"]
            if inc["status"] != "resolved":
                formatted_incidents.append(
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Name:* {name}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Status* {status}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Impact:* {impact}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Created:* {created_at}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Last Updated:* {updated_at}",
                            },
                        ],
                    }
                )
                formatted_incidents.append(
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": {
                                    "type": "plain_text",
                                    "text": "Open In Statuspage",
                                },
                                "url": shortlink,
                            },
                        ],
                    },
                )
                formatted_incidents.append({"type": "divider"})
    if len(formatted_incidents) == 0:
        return none_found_block
    else:
        for inc in formatted_incidents:
            base_block.append(inc)
        return {
            "channel": channel_id,
            "blocks": base_block,
        }


def return_help(channel_id: str) -> List[str]:
    """
    Help information
    """
    return {
        "channel": channel_id,
        "blocks": [
            {"type": "divider"},
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":robot_face: Incident Bot Help",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "To use any of these commands, simply mention me and then provide the command listed below. For example: `@Incident Bot lsai`",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*help:* This command that explains help options.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*lsoi:* List only incidents that are still *open* - as in non-resolved.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*lsai:* List *all* incidents regardless of status.",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*ls spinc:* List *open* Statuspage incidents (if the integration is enabled).",
                },
            },
        ],
    }
