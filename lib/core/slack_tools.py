import logging
import os

from dotenv import load_dotenv
from slack import WebClient, errors

logger = logging.getLogger(__name__)

# .env parse
dotenv_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
)
load_dotenv(dotenv_path)

slack_web_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
verification_token = os.getenv("SLACK_VERIFICATION_TOKEN")

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
