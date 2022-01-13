import logging
import pyjokes
import random
import string

from __main__ import __version__, config
from ..db import db
from ..incident import routes as inc
from ..statuspage import statuspage
from . import slack_tools
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

bot_user_id = slack_tools.slack_web_client.auth_test()["user_id"]

# Error events
@slack_tools.slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))


# React
@slack_tools.slack_events_adapter.on("reaction_added")
def reaction_added(event_data):
    # Automatically create incident based on reaction with specific emoji
    if config.incident_auto_create_from_react_enabled == "true":
        event = event_data["event"]
        emoji = event["reaction"]
        channel = event["item"]["channel"]
        ts = event["item"]["ts"]
        # Only act if the emoji is the one we care about
        if emoji == config.incident_auto_create_from_react_emoji_name:
            # Retrieve the content of the message that was reacted to
            try:
                result = slack_tools.slack_web_client.conversations_history(
                    channel=channel, inclusive=True, oldest=ts, limit=1
                )
                message = result["messages"][0]
                message_reacted_to_content = message["text"]
            except slack_tools.errors.SlackApiError as error:
                logger.error(f"Error when trying to retrieve a message: {error}")
            suffix = "".join(
                random.choices(string.ascii_lowercase + string.digits, k=6)
            )
            request_parameters = {
                "channel": channel,
                "channel_description": f"auto-{suffix}",
                "descriptor": f"auto-{suffix}",
                "user": "internal_auto_create",
                "token": slack_tools.verification_token,
                "message_reacted_to_content": message_reacted_to_content,
                "original_message_timestamp": ts,
            }
            # Create an incident based on the message using the internal path
            try:
                inc.create_incident(
                    internal=True, request_parameters=request_parameters
                )
            except Exception as error:
                logger.error(f"Error when trying to create an incident: {error}")


@slack_tools.slack_events_adapter.on("app_mention")
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
            try:
                slack_tools.slack_web_client.chat_postMessage(**resp)
            except slack_tools.errors.SlackApiError as error:
                logger.error(f"Error when trying to post help message: {error}")
    elif "lsoi" in message:
        channel = event["channel"]
        database_data = db.db_read_all_incidents()
        resp = format_incident_list_message(channel, database_data, all=False)
        try:
            slack_tools.slack_web_client.chat_postMessage(**resp)
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to list open incidents: {error}")
    elif "lsai" in message:
        channel = event["channel"]
        database_data = db.db_read_all_incidents()
        resp = format_incident_list_message(channel, database_data, all=True)
        try:
            slack_tools.slack_web_client.chat_postMessage(**resp)
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to list all incidents: {error}")
    elif "ls spinc" in " ".join(message):
        channel = event["channel"]
        if config.statuspage_integration_enabled == "true":
            sp_objects = statuspage.StatuspageObjects()
            sp_incidents = sp_objects.open_incidents
            resp = format_sp_incident_list_message(channel, sp_incidents)
            try:
                slack_tools.slack_web_client.chat_postMessage(**resp)
            except slack_tools.errors.SlackApiError as error:
                logger.error(
                    f"Error when trying to list open Statuspage incidents: {error}"
                )
        else:
            try:
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
            except slack_tools.errors.SlackApiError as error:
                logger.error(
                    f"Error when trying to list open Statuspage incidents: {error}"
                )
    elif "tell me a joke" in " ".join(message):
        channel = event["channel"]
        resp = pyjokes.get_joke()
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel,
                text=resp,
            )
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to send a joke: {error}")
    elif "ping" in message:
        channel = event["channel"]
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel,
                text="pong",
            )
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to respond to a ping: {error}")
    elif "version" in message:
        channel = event["channel"]
        try:
            slack_tools.slack_web_client.chat_postMessage(
                channel=channel,
                text=f"I am currently running version: {__version__}",
            )
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to print version: {error}")
    else:
        channel = event["channel"]
        requested = " ".join(message)
        try:
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
        except slack_tools.errors.SlackApiError as error:
            logger.error(f"Error when trying to state a command doesn't exist: {error}")


def format_incident_list_message(
    channel_id: str, incidents: List[Tuple], all: bool = False
) -> Dict[str, str]:
    """Return a message containing details on incidents

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    incidents -- List[Tuple] containing incident information
    all -- Bool indicating whether or not all incidents should be returned regardless of status
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
    """Return a message containing details on Statuspage incidents

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    incidents -- List[Dict[str, str]] containing Statuspage incident information
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
    """Return the help menu

    Keyword arguments:
    channel_id -- String containing the ID of the Slack channel to send the message to
    """
    base_block = [
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
                "text": f"To use any of these commands, simply mention me and then provide the command listed below. For example: `<@{bot_user_id}> lsai`",
            },
        },
        {"type": "divider"},
    ]
    commands = {
        "help": "This command that explains help options.",
        "lsai": "List *all* incidents regardless of status.",
        "lsoi": "List only incidents that are still *open* - as in non-resolved.",
        "ls spinc": "List *open* Statuspage incidents (if the integration is enabled)",
        "ping": "Ping the bot to check and see if it's alive and responding.",
        "version": "Have the bot respond with current application version.",
    }
    for key, value in commands.items():
        base_block.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{key}:* {value}",
                },
            },
        )
    return {
        "channel": channel_id,
        "blocks": base_block,
    }
