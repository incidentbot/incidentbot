from incidentbot.configuration.settings import settings
from incidentbot.exceptions import IndexNotFoundError
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface

from incidentbot.slack.messages import (
    BlockBuilder,
)
from incidentbot.util import gen
from slack_sdk.errors import SlackApiError
from typing import Any

if not settings.IS_TEST_ENVIRONMENT:
    from incidentbot.slack.client import (
        slack_web_client,
    )


def comms_reminder(channel_id: str):
    """
    Sends a message to a channel to initiate communications updates

    Parameters:
        channel_id (str): The incident channel id
    """

    try:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            blocks=BlockBuilder.comms_reminder_message(),
            text="Some time has passed since this incident was declared. How about updating others on its status?",
        )
    except SlackApiError as error:
        logger.error(
            f"error sending comms reminder message to incident channel: {error}"
        )


def extract_role_owner(message_blocks: dict[Any, Any], block_id: str) -> str:
    """
    Takes message blocks and a block_id and returns information specific
    to one of the role blocks

    Parameters:
        message_block (dict[Any, Any]): Message blocks to search
        block_id (str): Block id to match
    """

    index = gen.find_index_in_list(message_blocks, "block_id", block_id)
    if index == -1:
        raise IndexNotFoundError(
            f"Could not find index for block_id {block_id}"
        )

    return (
        message_blocks[index]["text"]["text"].split("\n")[1].replace(" ", "")
    )


def role_watcher(channel_id: str):
    """
    Sends a message to a channel if roles remain unassigned

    Parameters:
        channel_id (str): The incident channel id
    """

    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    participants = IncidentDatabaseInterface.list_participants(record)

    if not participants:
        try:
            slack_web_client.chat_postMessage(
                channel=channel_id,
                blocks=BlockBuilder.role_assignment_message(),
                text="No roles have been assigned for this incident yet. Please review, assess, and claim as-needed.",
            )
        except SlackApiError as error:
            logger.error(
                f"error sending role watcher message to incident channel: {error}"
            )
