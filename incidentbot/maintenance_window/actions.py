import uuid

from incidentbot.logging import logger
from incidentbot.models.maintenance_window import (
    MaintenanceWindowDatabaseInterface,
)
from incidentbot.slack.client import (
    slack_web_client,
)
from incidentbot.slack.messages import BlockBuilder
from slack_sdk.errors import SlackApiError

err_msg = ":robot_face::heart_on_fire: I've run into a problem processing commands for this incident: I cannot find it in the database. Let an administrator know about this error."

"""
Functions for handling inbound actions
"""


async def set_status(
    id: uuid.UUID,
    status: str,
):
    """
    Parameters:
        id (uuid.UUID): Maintenance window ID to match
        status (str): The status value
    """

    maintenance_window = MaintenanceWindowDatabaseInterface.get_one(id)

    if maintenance_window:
        # Send message to each channel subscribed to the maintenance window
        for channel_id in maintenance_window.channels:
            try:
                slack_web_client.chat_postMessage(
                    channel=channel_id,
                    blocks=BlockBuilder.maintenance_window_notification(
                        record=maintenance_window,
                        status=status,
                    ),
                    text=f"Maintenance window {maintenance_window.title} has changed to {status}.",
                )
            except SlackApiError as error:
                logger.error(
                    f"Error sending maintenance window status update to channel: {error}"
                )

        # Update incident record with new status
        try:
            MaintenanceWindowDatabaseInterface.set_status(
                id=maintenance_window.id,
                status=status,
            )
        except Exception as error:
            logger.fatal(f"Error updating entry in database: {error}")
