import datetime
import json
import logging

from __main__ import config
from slack import WebClient, errors
from typing import Dict

logger = logging.getLogger(__name__)

# Initialize Slack clients
verification_token = config.slack_verification_token
slack_web_client = WebClient(token=config.slack_bot_token)

"""
Reusable variables
"""
all_workspace_groups = slack_web_client.usergroups_list()


def get_channel_history(channel_id: str) -> str:
    """Return the history of a Slack channel as a json string object

    Keyword arguments:
    channel_id -- The ID of the Slack channel to retrieve history from
    """
    history_dict = slack_web_client.conversations_history(channel=channel_id)[
        "messages"
    ]
    history_dict_reversed = []
    for item in reversed(history_dict):
        history_dict_reversed.append(item)
    return json.dumps(history_dict_reversed)


def get_formatted_channel_history(channel_id: str, channel_name: str) -> str:
    """Return the history of a Slack channel as a formatted string

    Keyword arguments:
    channel_id -- The ID of the Slack channel to retrieve history from
    channel_name -- The name of the Slack channel to retrieve history from
    """
    users = slack_web_client.users_list()["members"]
    replaced_messages_string = replace_user_ids(get_channel_history(channel_id), users)
    formatted_channel_history = str()
    formatted_channel_history += f"Slack channel history for incident {channel_name}\n"
    for message in replaced_messages_string:
        user = message["user"]
        text = message["text"]
        timestamp = datetime.datetime.fromtimestamp(int(message["ts"].split(".")[0]))
        prefix = f"* {timestamp}"
        if "has joined the channel" in text:
            formatted_channel_history += f"{prefix} {user} joined the channel\n"
        elif "set the channel topic" in text:
            formatted_channel_history += f"{prefix} {user} {text}\n"
        elif "This content can't be displayed." in text:
            pass
        else:
            formatted_channel_history += f"{prefix} {user}: {text}\n"
    return formatted_channel_history


def replace_user_ids(json_string: str, user_list: Dict[str, str]) -> str:
    """Replace a user's ID with their name and return a json string object"""
    for user in user_list:
        real_name = user["profile"]["real_name"]
        user_id = user["id"]
        json_string = json_string.replace(user_id, real_name)
    return json.loads(json_string)


def return_slack_channel_info() -> Dict[str, str]:
    """Return a list of Slack channels"""
    try:
        return slack_web_client.conversations_list(exclude_archived=True, limit=500)[
            "channels"
        ]
    except errors.SlackApiError as error:
        logger.error(f"Error getting channel list from Slack workspace: {error}")
