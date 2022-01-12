import logging

from __main__ import app, config
from slack import WebClient, errors
from slackeventsapi import SlackEventAdapter

logger = logging.getLogger(__name__)

# Initialize Slack clients
verification_token = config.slack_verification_token
slack_events_adapter = SlackEventAdapter(
    config.slack_signing_secret, "/slack/events", server=app
)
slack_web_client = WebClient(token=config.slack_bot_token)

"""
Reusable variables
"""
all_workspace_groups = slack_web_client.usergroups_list()


def return_slack_channel_info():
    try:
        return slack_web_client.conversations_list(exclude_archived=True, limit=500)[
            "channels"
        ]
    except errors.SlackApiError as error:
        logger.error(f"Error getting channel list from Slack workspace: {error}")
